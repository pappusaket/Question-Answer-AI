# auth.py - SIMPLIFIED
from datetime import datetime, timedelta
import os
import jwt  # python-jose package

SECRET_KEY = os.getenv("SECRET_KEY", "test-secret-key-123")
ALGORITHM = "HS256"

def create_access_token(data: dict):
    """Simple token creation"""
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=7)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
