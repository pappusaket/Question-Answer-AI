# auth.py - WITH IMPROVED TOKEN EXPIRY HANDLING
from jose import JWTError, jwt
from datetime import datetime, timedelta
from fastapi import HTTPException, status, Depends
from fastapi.security import HTTPBearer
from sqlalchemy.orm import Session
import os
import database
import models

SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_DAYS = 7

security = HTTPBearer()

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=ACCESS_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def verify_token(token: str):
    """
    Token verify karein aur specific errors return karein
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return {"valid": True, "payload": payload, "error": None}
    except jwt.ExpiredSignatureError:
        return {"valid": False, "payload": None, "error": "Token expired"}
    except jwt.JWTError:
        return {"valid": False, "payload": None, "error": "Invalid token"}
    except Exception as e:
        return {"valid": False, "payload": None, "error": f"Token verification failed: {str(e)}"}

def get_current_user(
    credentials: str = Depends(security),
    db: Session = Depends(database.get_db)
):
    """
    Improved current user function with better error messages
    """
    token = credentials.credentials
    
    # Token verify karein
    token_result = verify_token(token)
    
    if not token_result["valid"]:
        error_msg = token_result["error"]
        
        if "expired" in error_msg.lower():
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Your session has expired. Please login again.",
                headers={"WWW-Authenticate": "Bearer"},
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication token. Please login again.",
                headers={"WWW-Authenticate": "Bearer"},
            )
    
    # User fetch karein
    user_id = token_result["payload"].get("user_id")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return user

# ✅ TOKEN INFO ENDPOINT KE LIYE HELPER FUNCTION
def get_token_info(token: str):
    """
    Token ki information provide karein (expiry date, user_id, etc.)
    """
    token_result = verify_token(token)
    
    if token_result["valid"]:
        payload = token_result["payload"]
        expiry_timestamp = payload.get("exp")
        expiry_date = datetime.fromtimestamp(expiry_timestamp) if expiry_timestamp else None
        
        return {
            "valid": True,
            "user_id": payload.get("user_id"),
            "expires_at": expiry_date.isoformat() if expiry_date else None,
            "days_remaining": (expiry_date - datetime.utcnow()).days if expiry_date else 0,
            "message": "Token is valid"
        }
    else:
        return {
            "valid": False,
            "error": token_result["error"],
            "message": "Token is invalid"
        }
