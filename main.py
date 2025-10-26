from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
import os
import random
from database import get_db, engine
import models
import schemas
from auth import create_access_token, get_current_user, hash_password, verify_password

# Create tables
models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="Question-AI", version="1.0.0")

@app.get("/")
def home():
    return {"message": "Question AI API is running!", "status": "active"}

@app.get("/health")
def health_check():
    return {"status": "healthy"}

# ✅ CREATE USER WITH PASSWORD HASHING
@app.get("/create-test-user")
def create_test_user(db: Session = Depends(get_db)):
    """Test user create karne ke liye simple GET endpoint"""
    test_email = f"test{random.randint(1000,9999)}@example.com"
    
    new_user = models.User(
        email=test_email, 
        password=hash_password("test123")  # ✅ Password hashed
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    return {
        "message": "Test user created successfully", 
        "user_id": new_user.id, 
        "email": test_email
    }

# ✅ LOGIN ENDPOINT (GET - Browser testable)
@app.get("/login-test")
def login_test(db: Session = Depends(get_db)):
    """Login test karne ke liye GET endpoint"""
    user = db.query(models.User).first()
    if not user:
        return {"message": "Pehle /create-test-user par jaake user create karein"}
    
    # Test password verification
    password_correct = verify_password("test123", user.password)
    
    if password_correct:
        access_token = create_access_token({"user_id": user.id})
        return {
            "message": "Login successful!",
            "user_id": user.id,
            "email": user.email,
            "access_token": access_token,
            "token_type": "bearer"
        }
    else:
        return {"message": "Password verification failed"}

# ✅ PROTECTED PROFILE ENDPOINT
@app.get("/profile")
def get_profile(current_user: models.User = Depends(get_current_user)):
    return {
        "message": "Protected route accessed successfully",
        "user_id": current_user.id, 
        "email": current_user.email
    }

@app.get("/test-db")
def test_db(db: Session = Depends(get_db)):
    user_count = db.query(models.User).count()
    return {"database_status": "connected", "total_users": user_count}

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=port)
