# auth.py - CORRECTED
from datetime import datetime, timedelta
from fastapi import HTTPException, Depends
from fastapi.security import HTTPBearer
from sqlalchemy.orm import Session
import os
from jose import jwt, JWTError  # ✅ Correct import
import database
import models

SECRET_KEY = os.getenv("SECRET_KEY", "test-secret-key-123")
ALGORITHM = "HS256"

security = HTTPBearer()

def create_access_token(data: dict):
    """Simple token creation"""
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=7)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def get_current_user(
    credentials: str = Depends(security),
    db: Session = Depends(database.get_db)
):
    """Simple user verification"""
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("user_id")
        user = db.query(models.User).filter(models.User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        return user
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")
