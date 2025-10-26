# main.py - Debug version
from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
import os
import random
import traceback
from database import get_db, engine
import models

# Create tables
models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="Question-AI", version="1.0.0")

@app.get("/")
def home():
    return {"message": "Question AI API is running!", "status": "active"}

@app.get("/health")
def health_check():
    return {"status": "healthy"}

# ✅ SIMPLE CREATE USER (Without auth dependencies)
@app.get("/create-test-user")
def create_test_user(db: Session = Depends(get_db)):
    """Simple test user without any external dependencies"""
    try:
        test_email = f"test{random.randint(1000,9999)}@example.com"
        
        new_user = models.User(
            email=test_email, 
            password="test123"  # Plain password for now
        )
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        
        return {
            "message": "Test user created successfully", 
            "user_id": new_user.id, 
            "email": test_email
        }
    except Exception as e:
        return {"error": str(e), "traceback": traceback.format_exc()}

# ✅ SIMPLE LOGIN TEST (Without auth)
@app.get("/login-test")
def login_test(db: Session = Depends(get_db)):
    """Simple login without token generation"""
    try:
        user = db.query(models.User).first()
        if not user:
            return {"message": "No users found"}
        
        return {
            "message": "User found",
            "user_id": user.id,
            "email": user.email,
            "stored_password": user.password
        }
    except Exception as e:
        return {"error": str(e), "traceback": traceback.format_exc()}

@app.get("/test-db")
def test_db(db: Session = Depends(get_db)):
    user_count = db.query(models.User).count()
    return {"database_status": "connected", "total_users": user_count}

# ✅ CHECK IMPORTS
@app.get("/check-imports")
def check_imports():
    """Check if all imports are working"""
    try:
        import auth
        import schemas
        return {"imports": "successful"}
    except Exception as e:
        return {"imports": "failed", "error": str(e)}

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=port)
