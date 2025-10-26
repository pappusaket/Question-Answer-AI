# main.py - DEBUG LOGIN
from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
import os
import random
import traceback
from database import get_db, engine
import models
from auth import create_access_token, get_current_user

# Create tables
models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="Question-AI", version="1.0.0")

@app.get("/")
def home():
    return {"message": "Question AI API is running!", "status": "active"}

@app.get("/health")
def health_check():
    return {"status": "healthy"}

# ✅ CREATE USER
@app.get("/create-test-user")
def create_test_user(db: Session = Depends(get_db)):
    test_email = f"test{random.randint(1000,9999)}@example.com"
    
    new_user = models.User(email=test_email, password="test123")
    db.add(new_user)
    db.commit()
    
    return {
        "message": "Test user created successfully", 
        "user_id": new_user.id, 
        "email": test_email
    }

# ✅ LOGIN WITH ERROR HANDLING
@app.get("/login-test")
def login_test(db: Session = Depends(get_db)):
    try:
        user = db.query(models.User).first()
        if not user:
            return {"message": "No users found"}
        
        # Generate token
        access_token = create_access_token({"user_id": user.id})
        
        return {
            "message": "Login successful!",
            "user_id": user.id,
            "email": user.email,
            "access_token": access_token,
            "token_type": "bearer"
        }
    except Exception as e:
        return {"error": str(e), "traceback": traceback.format_exc()}

# ✅ SIMPLE PROFILE (No token required for testing)
@app.get("/simple-profile")
def simple_profile(db: Session = Depends(get_db)):
    user = db.query(models.User).first()
    if user:
        return {"user_id": user.id, "email": user.email}
    return {"message": "No user found"}

# ✅ PROTECTED PROFILE
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
