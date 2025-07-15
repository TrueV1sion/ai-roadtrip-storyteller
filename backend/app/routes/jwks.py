"""
JWKS (JSON Web Key Set) endpoint for JWT public key distribution.
This allows clients to verify JWT tokens using the public keys.
"""
from fastapi import APIRouter
from typing import Dict, Any
from app.core.jwt_manager import jwt_manager

router = APIRouter()


@router.get("/.well-known/jwks.json", response_model=Dict[str, Any])
async def get_jwks():
    """
    Get the JSON Web Key Set (JWKS) containing public keys for JWT verification.
    
    This endpoint is used by clients to fetch the public keys needed to verify
    JWT tokens issued by this server. It follows the JWKS standard format.
    
    Returns:
        Dict containing the public keys in JWKS format
    """
    return jwt_manager.get_public_keys()


@router.post("/api/auth/rotate-keys", include_in_schema=False)
async def rotate_keys():
    """
    Rotate JWT signing keys (admin only).
    
    This endpoint should be protected and only accessible by administrators.
    It generates new RSA key pairs for JWT signing while keeping old keys
    for verification of existing tokens.
    
    Returns:
        Dict with the new key ID
    """
    # TODO: Add admin authentication check here
    new_key_id = jwt_manager.rotate_keys()
    return {"message": "Keys rotated successfully", "new_key_id": new_key_id}