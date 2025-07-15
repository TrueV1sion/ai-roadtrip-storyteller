# Debug and Logging Standards

## Production Code Standards

### ❌ NEVER Do This in Production

```python
# NEVER log sensitive parameters
logger.debug(f"Query: {query} with parameters: {params}")
logger.debug(f"User {user_id} preferences: {preferences}")

# NEVER use print statements
print("Starting server...")
print(f"Result: {result}")

# NEVER log authentication data
logger.debug(f"Token: {token}")
logger.debug(f"Password validation for {username}")
```

### ✅ DO This Instead

```python
# Log operations without sensitive data
logger.debug("Database query executed successfully")
logger.debug("User preferences updated")

# Use proper logging levels
logger.info("Server started successfully")
logger.info("Operation completed")

# Log metadata only
logger.debug("Authentication attempt")
logger.debug("Token validation completed")
```

## Logging Levels Guide

### DEBUG
- Development and troubleshooting only
- Should be disabled in production
- Use for detailed diagnostic information

### INFO
- Normal application flow
- Key business events
- Startup/shutdown messages

### WARNING
- Recoverable issues
- Deprecated feature usage
- Performance concerns

### ERROR
- Exceptions and errors
- Failed operations
- Always include stack traces

### CRITICAL
- System failures
- Data corruption risks
- Security breaches

## Security Guidelines

### Never Log:
- Passwords or authentication tokens
- API keys or secrets
- Personal identifiable information (PII)
- Credit card or payment data
- Full database queries with parameters
- User session data

### Safe to Log:
- User IDs (not usernames)
- Operation types
- Timestamps
- Error codes
- Performance metrics
- Request IDs

## Best Practices

### 1. Use Structured Logging
```python
logger.info(
    "API request processed",
    extra={
        "request_id": request_id,
        "method": "POST",
        "path": "/api/endpoint",
        "duration_ms": 45,
        "status_code": 200
    }
)
```

### 2. Sanitize Dynamic Content
```python
# Bad
logger.error(f"Failed to process: {user_input}")

# Good
logger.error(
    "Failed to process user input",
    extra={"input_length": len(user_input)}
)
```

### 3. Use Log Context
```python
import contextvars

request_id = contextvars.ContextVar('request_id', default=None)

# Set context
request_id.set(str(uuid.uuid4()))

# Logs automatically include request_id
logger.info("Processing request")
```

### 4. Performance Considerations
```python
# Check log level before expensive operations
if logger.isEnabledFor(logging.DEBUG):
    expensive_debug_info = calculate_debug_metrics()
    logger.debug(f"Metrics: {expensive_debug_info}")
```

## Demo and Test Code

### Isolate Demo Code
```python
# Put demos in separate files or clearly marked sections
# examples/demo_feature.py

def demo():
    print("This is a demo")  # OK in demo files

if __name__ == "__main__":
    demo()
```

### Test Logging
```python
# In tests, use caplog fixture
def test_feature(caplog):
    with caplog.at_level(logging.DEBUG):
        my_function()
    assert "expected message" in caplog.text
```

## Pre-commit Hooks

The following checks are enforced:

1. **No print statements** in production code
2. **No console.log** in JavaScript/TypeScript
3. **No sensitive parameter logging**
4. **No debug statements** (pdb, debugger)

## Monitoring and Compliance

### Regular Audits
- Weekly automated scans for debug artifacts
- Quarterly security review of logging practices
- Annual training on secure logging

### Metrics to Track
- Debug statements per release
- Security violations caught
- Log volume trends
- Mean time to detect issues

## Migration Guide

### Cleaning Existing Code
1. Run debug cleanup scripts
2. Review and update logging statements
3. Add appropriate log levels
4. Test in staging environment
5. Deploy with monitoring

### Tools
- `backend/app/core/debug_cleanup.py` - Automated cleanup
- Pre-commit hooks - Prevention
- Log analysis tools - Detection

## Questions?

Contact the security team for clarification on logging standards or to request exceptions for specific use cases.