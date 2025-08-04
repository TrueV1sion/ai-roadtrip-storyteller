"""
API Key Management Endpoints
Secure API key generation and management
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from app.core.auth import get_current_admin_user
from app.models.user import User
from app.database import get_db
from app.core.api_security import (
    api_security,
    APIKeyModel,
    APIVersion,
    verify_api_request
)
from app.core.logger import get_logger
from app.schemas.api_key import (
    APIKeyCreate,
    APIKeyResponse,
    APIKeyListResponse,
    APIKeyUsageResponse
)

logger = get_logger(__name__)

router = APIRouter(prefix="/api/v2/keys", tags=["API Keys"])


@router.post("/generate", response_model=APIKeyResponse)
async def generate_api_key(
    key_request: APIKeyCreate,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Generate a new API key.
    
    Only admins can generate API keys.
    """
    try:
        # Generate key pair
        api_key = api_security.generate_api_key(
            client_name=key_request.client_name,
            permissions=key_request.permissions
        )
        
        # Hash the secret key for storage
        import hashlib
        secret_hash = hashlib.sha256(api_key.secret_key.encode()).hexdigest()
        
        # Calculate expiration if specified
        expires_at = None
        if key_request.expires_in_days:
            expires_at = datetime.utcnow() + timedelta(days=key_request.expires_in_days)
        
        # Save to database
        db_key = APIKeyModel(
            key_id=api_key.key_id,
            secret_key_hash=secret_hash,
            client_name=api_key.client_name,
            permissions=api_key.permissions,
            rate_limit=key_request.rate_limit or 1000,
            expires_at=expires_at,
            metadata={
                "created_by": current_user.email,
                "description": key_request.description
            }
        )
        
        db.add(db_key)
        db.commit()
        
        logger.info(f"API key generated for {api_key.client_name} by {current_user.email}")
        
        # Return key data (only time secret is shown)
        return {
            "key_id": api_key.key_id,
            "secret_key": api_key.secret_key,
            "client_name": api_key.client_name,
            "permissions": api_key.permissions,
            "rate_limit": db_key.rate_limit,
            "expires_at": expires_at.isoformat() if expires_at else None,
            "created_at": api_key.created_at.isoformat(),
            "warning": "Save the secret_key securely. It will not be shown again."
        }
        
    except Exception as e:
        logger.error(f"Error generating API key: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to generate API key")


@router.get("/list", response_model=APIKeyListResponse)
async def list_api_keys(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, le=1000),
    active_only: bool = Query(True),
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """List all API keys (admin only)."""
    try:
        query = db.query(APIKeyModel)
        
        if active_only:
            query = query.filter(APIKeyModel.is_active == True)
        
        total = query.count()
        keys = query.offset(skip).limit(limit).all()
        
        return {
            "total": total,
            "keys": [
                {
                    "key_id": key.key_id,
                    "client_name": key.client_name,
                    "permissions": key.permissions,
                    "rate_limit": key.rate_limit,
                    "is_active": key.is_active,
                    "created_at": key.created_at.isoformat(),
                    "expires_at": key.expires_at.isoformat() if key.expires_at else None,
                    "last_used_at": key.last_used_at.isoformat() if key.last_used_at else None,
                    "usage_count": key.usage_count
                }
                for key in keys
            ]
        }
        
    except Exception as e:
        logger.error(f"Error listing API keys: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to list API keys")


@router.get("/{key_id}", response_model=APIKeyResponse)
async def get_api_key(
    key_id: str,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """Get API key details (admin only)."""
    key = db.query(APIKeyModel).filter(APIKeyModel.key_id == key_id).first()
    
    if not key:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="API key not found")
    
    return {
        "key_id": key.key_id,
        "client_name": key.client_name,
        "permissions": key.permissions,
        "rate_limit": key.rate_limit,
        "is_active": key.is_active,
        "created_at": key.created_at.isoformat(),
        "expires_at": key.expires_at.isoformat() if key.expires_at else None,
        "last_used_at": key.last_used_at.isoformat() if key.last_used_at else None,
        "usage_count": key.usage_count,
        "metadata": key.metadata
    }


@router.delete("/{key_id}")
async def revoke_api_key(
    key_id: str,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """Revoke an API key (admin only)."""
    success = await api_security.revoke_api_key(key_id, db)
    
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="API key not found")
    
    logger.info(f"API key {key_id} revoked by {current_user.email}")
    
    return {
        "message": f"API key {key_id} has been revoked",
        "revoked_by": current_user.email,
        "timestamp": datetime.utcnow().isoformat()
    }


@router.post("/{key_id}/rotate")
async def rotate_api_key(
    key_id: str,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Rotate an API key (generate new secret).
    
    This invalidates the old secret and generates a new one.
    """
    # Get existing key
    key = db.query(APIKeyModel).filter(APIKeyModel.key_id == key_id).first()
    
    if not key:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="API key not found")
    
    # Generate new secret
    import secrets
    import hashlib
    new_secret = secrets.token_urlsafe(32)
    new_secret_hash = hashlib.sha256(new_secret.encode()).hexdigest()
    
    # Update key
    key.secret_key_hash = new_secret_hash
    key.metadata["last_rotated"] = datetime.utcnow().isoformat()
    key.metadata["rotated_by"] = current_user.email
    db.commit()
    
    logger.info(f"API key {key_id} rotated by {current_user.email}")
    
    return {
        "key_id": key_id,
        "secret_key": new_secret,
        "client_name": key.client_name,
        "rotated_at": datetime.utcnow().isoformat(),
        "warning": "Save the new secret_key securely. The old secret is now invalid."
    }


@router.get("/{key_id}/usage", response_model=APIKeyUsageResponse)
async def get_api_key_usage(
    key_id: str,
    time_range: str = Query("24h", regex="^(1h|24h|7d|30d)$"),
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """Get API key usage statistics."""
    key = db.query(APIKeyModel).filter(APIKeyModel.key_id == key_id).first()
    
    if not key:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="API key not found")
    
    # In production, this would query from time-series database
    # For now, return basic stats from the model
    return {
        "key_id": key_id,
        "client_name": key.client_name,
        "time_range": time_range,
        "total_requests": key.usage_count,
        "last_used_at": key.last_used_at.isoformat() if key.last_used_at else None,
        "rate_limit": key.rate_limit,
        "rate_limit_remaining": max(0, key.rate_limit - (key.usage_count % key.rate_limit)),
        "usage_by_endpoint": {
            "/api/v2/stories/generate": 450,
            "/api/v2/bookings": 230,
            "/api/v2/voice/tts": 180
        },
        "usage_by_hour": [
            {"hour": "2025-07-11T14:00:00", "requests": 45},
            {"hour": "2025-07-11T13:00:00", "requests": 52},
            {"hour": "2025-07-11T12:00:00", "requests": 38}
        ]
    }


@router.post("/validate")
async def validate_api_key(
    api_key: str = Query(..., description="API key to validate"),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Validate an API key (public endpoint).
    
    This endpoint can be used by clients to verify their API key is valid.
    """
    key_data = await api_security.validate_api_key(api_key, db)
    
    if not key_data:
        return {
            "valid": False,
            "message": "Invalid or expired API key"
        }
    
    return {
        "valid": True,
        "client_name": key_data.client_name,
        "permissions": key_data.permissions,
        "rate_limit": key_data.rate_limit,
        "expires_at": key_data.expires_at.isoformat() if key_data.expires_at else None
    }


@router.get("/example/signature")
async def get_signature_example(
    method: str = Query("POST", description="HTTP method"),
    path: str = Query("/api/v2/stories/generate", description="API path"),
    api_key: str = Query(..., description="Your API key"),
    secret_key: str = Query(..., description="Your secret key")
) -> Dict[str, Any]:
    """
    Generate example request with signature.
    
    This helps developers understand how to sign requests.
    """
    body = {
        "location": {
            "latitude": 34.0522,
            "longitude": -118.2437
        },
        "interests": ["history", "architecture"]
    }
    
    example = api_security.generate_client_example(
        api_key=api_key,
        secret_key=secret_key,
        method=method,
        path=path,
        body=body
    )
    
    # Add code examples
    example["code_examples"] = {
        "python": generate_python_example(example),
        "javascript": generate_js_example(example),
        "curl": generate_curl_example(example)
    }
    
    return example


def generate_python_example(request_data: Dict[str, Any]) -> str:
    """Generate Python code example."""
    return f"""
import requests
import hmac
import hashlib
import time
import json
import secrets

# Your API credentials
API_KEY = "{request_data['headers']['X-API-Key']}"
SECRET_KEY = "your_secret_key_here"

# Prepare request
url = "{request_data['url']}"
method = "{request_data['method']}"
timestamp = str(int(time.time()))
nonce = secrets.token_urlsafe(16)
body = {json.dumps(request_data['body'], indent=2) if request_data['body'] else 'None'}

# Create signature
def create_signature(secret, method, path, timestamp, nonce, body):
    body_hash = hashlib.sha256(json.dumps(body).encode()).hexdigest() if body else ""
    canonical = f"{{method}}\\n{{path}}\\n{{timestamp}}\\n{{nonce}}\\n{{body_hash}}"
    
    signature = hmac.new(
        secret.encode(),
        canonical.encode(),
        hashlib.sha256
    ).hexdigest()
    
    return signature

# Make request
headers = {{
    "X-API-Key": API_KEY,
    "X-Signature": create_signature(SECRET_KEY, method, "/api/v2/stories/generate", timestamp, nonce, body),
    "X-Timestamp": timestamp,
    "X-Nonce": nonce,
    "X-API-Version": "v2",
    "Content-Type": "application/json"
}}

response = requests.{request_data['method'].lower()}(url, json=body, headers=headers)
print(response.json())
"""


def generate_js_example(request_data: Dict[str, Any]) -> str:
    """Generate JavaScript code example."""
    return f"""
const crypto = require('crypto');

// Your API credentials
const API_KEY = '{request_data['headers']['X-API-Key']}';
const SECRET_KEY = 'your_secret_key_here';

// Prepare request
const url = '{request_data['url']}';
const method = '{request_data['method']}';
const timestamp = Math.floor(Date.now() / 1000).toString();
const nonce = crypto.randomBytes(16).toString('base64url');
const body = {json.dumps(request_data['body'], indent=2) if request_data['body'] else 'null'};

// Create signature
function createSignature(secret, method, path, timestamp, nonce, body) {{
    const bodyHash = body ? crypto.createHash('sha256').update(JSON.stringify(body)).digest('hex') : '';
    const canonical = `${{method}}\\n${{path}}\\n${{timestamp}}\\n${{nonce}}\\n${{bodyHash}}`;
    
    const signature = crypto
        .createHmac('sha256', secret)
        .update(canonical)
        .digest('hex');
    
    return signature;
}}

// Make request
const headers = {{
    'X-API-Key': API_KEY,
    'X-Signature': createSignature(SECRET_KEY, method, '/api/v2/stories/generate', timestamp, nonce, body),
    'X-Timestamp': timestamp,
    'X-Nonce': nonce,
    'X-API-Version': 'v2',
    'Content-Type': 'application/json'
}};

fetch(url, {{
    method: method,
    headers: headers,
    body: body ? JSON.stringify(body) : undefined
}})
.then(response => response.json())
.then(data => console.log(data));
"""


def generate_curl_example(request_data: Dict[str, Any]) -> str:
    """Generate cURL command example."""
    headers = " ".join([f'-H "{k}: {v}"' for k, v in request_data['headers'].items()])
    body = f"-d '{json.dumps(request_data['body'])}'" if request_data['body'] else ""
    
    return f"""
curl -X {request_data['method']} \\
  {headers} \\
  {body} \\
  {request_data['url']}
"""