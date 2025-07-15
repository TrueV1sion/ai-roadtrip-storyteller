# Authorization System Documentation

This document outlines the authorization system implemented in the AI Road Trip Storyteller application. The system provides robust mechanisms for controlling access to resources based on user roles and ownership.

## Core Concepts

### 1. User Roles

The application supports the following user roles, defined in an enumeration:

- **Admin**: Has full access to all resources and operations
- **Premium**: Paid users with access to premium features
- **Standard**: Regular users with standard permissions
- **Guest**: Limited access for unauthenticated or trial users

### 2. Resources

Resources that can be protected include:

- Users
- Stories
- Experiences
- Preferences
- Itineraries
- Games

### 3. Actions

The system controls access based on the following actions:

- Create
- Read
- Update
- Delete
- List

## Implementation Components

### Authentication

Authentication is handled through JWT tokens, with the following components:

1. **Token Types**:
   - Access tokens (short-lived)
   - Refresh tokens (longer-lived)

2. **Token Storage**:
   - Secure HTTP-only cookies
   - Local storage on the client side

3. **Token Validation**:
   - Token signature validation
   - Expiration checking
   - Token type verification
   - Blacklist checking for revoked tokens

### Authorization

The authorization system consists of several layers:

1. **User Authentication**: Verifying the identity of the user
2. **Permission Checking**: Determining if a user can perform an action on a resource
3. **Resource Filtering**: Limiting results based on user permissions
4. **Data Validation**: Ensuring input data doesn't bypass authorization

## Key Components

### 1. `get_current_user` Dependency

```python
async def get_current_user(token: Optional[str] = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User:
    """Get the current authenticated user or raise an exception."""
    # Validates the token and returns the corresponding user
    # Raises 401 Unauthorized if invalid or missing token
```

### 2. `get_current_active_user` Dependency

```python
async def get_current_active_user(current_user: User = Depends(get_current_user)) -> User:
    """Get the current authenticated user and verify they are active."""
    # Checks if the user account is active
    # Raises 403 Forbidden if account is inactive
```

### 3. `has_role` Dependency Factory

```python
def has_role(required_role: UserRole):
    """Dependency factory that checks if the current user has the required role."""
    # Creates a dependency that validates the user has at least the specified role
    # Used for role-based access control
```

Example usage:
```python
@router.get("/admin-endpoint", dependencies=[Depends(has_role(UserRole.ADMIN))])
async def admin_only_endpoint():
    # Only accessible to admins
```

### 4. `ResourcePermission` Class

A flexible permission system for checking and filtering access to resources:

```python
class ResourcePermission:
    """A flexible permission checker for resources."""
    
    def __init__(self, resource_type: ResourceType, action: Action, owner_field: str = "user_id"):
        # Initialize with the resource type, action, and owner field
    
    async def check(self, resource_id: Optional[str] = None, current_user: User = Depends(...)) -> bool:
        # Check if user can perform the action on the resource
        # Raises 403 Forbidden if not allowed
    
    def filter_query(self, query, user: User):
        # Filter a query based on user permissions
        # Returns a modified query that only includes accessible resources
```

Example usage:
```python
# Create a permission checker
story_read_permission = ResourcePermission(ResourceType.STORY, Action.READ)

@router.get("/stories/{story_id}", dependencies=[Depends(story_read_permission.check)])
async def get_story(story_id: str):
    # Only accessible if user has permission to read this story
```

## Authorization Flow

1. **Request Arrives**: The server receives a request to a protected endpoint
2. **Authentication**: The `get_current_user` dependency extracts and validates the JWT token
3. **User Lookup**: The system retrieves the user from the database
4. **Permission Check**: The permission system verifies the user can perform the requested action
5. **Resource Access**: If authorized, the user accesses the resource
6. **Response Filtering**: Any response data is filtered based on user permissions

## Role-Based Access Control Rules

The default permission matrix is as follows:

| Role     | Create | Read | Update | Delete | List |
|----------|--------|------|--------|--------|------|
| Admin    | ✅     | ✅   | ✅     | ✅     | ✅   |
| Premium  | ✅     | ✅   | ✅     | ✅     | ✅   |
| Standard | ✅     | ✅   | ✅     | ✅     | ✅   |
| Guest    | ❌     | ✅   | ❌     | ❌     | ✅   |

These rules are configurable per resource type and can be overridden when creating a `ResourcePermission` instance.

## Ownership-Based Access Control

Beyond role-based permissions, the system also enforces ownership-based controls:

- Users can only modify their own resources (unless they are admins)
- Resource queries are automatically filtered to only include resources owned by the user or those marked as public

## Rate Limiting

The authorization system is integrated with rate limiting:

- Standard users have limits on certain operations (e.g., 10 story generations per day)
- Premium users have higher or unlimited quotas
- Admins are not subject to rate limits

## Security Considerations

1. **Principle of Least Privilege**: Users receive only the minimum permissions needed
2. **Defense in Depth**: Multiple layers of checks prevent authorization bypasses
3. **Secure by Default**: Endpoints are protected by default, requiring explicit configuration to allow public access
4. **Audit Logging**: All permission denials are logged for security monitoring

## API Usage Examples

### Protected Endpoint

```python
@router.post("/stories")
async def create_story(
    story_data: StoryCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
    _: bool = Depends(story_permission.check)
):
    """Create a new story (requires authentication and authorization)."""
    # Implementation...
```

### Admin-Only Endpoint

```python
@router.get("/users", dependencies=[Depends(has_role(UserRole.ADMIN))])
async def list_all_users(db: Session = Depends(get_db)):
    """List all users (admin only)."""
    # Implementation...
```

### Owner-Only Access

```python
@router.put("/stories/{story_id}")
async def update_story(
    story_id: str,
    story_update: StoryUpdate,
    db: Session = Depends(get_db),
    _: bool = Depends(story_update_permission.check)  # Checks ownership
):
    """Update a story (only owner or admin)."""
    # Implementation...
```

## Best Practices for Developers

1. **Always use the authorization system**: Never bypass the permission checks
2. **Check at the controller level**: Place authorization checks in route handlers, not in services
3. **Use dependency injection**: Utilize FastAPI's dependency injection for permission checks
4. **Be explicit about permissions**: Document required permissions for each endpoint
5. **Test authorization rules**: Write tests specifically for authorization logic
6. **Consider permission impact**: When adding new features, consider the authorization implications