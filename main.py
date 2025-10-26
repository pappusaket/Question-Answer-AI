from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
import os
import random
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

# ✅ SIMPLE TEST ENDPOINT - Without auth dependencies
@app.get("/create-test-user")
def create_test_user(db: Session = Depends(get_db)):
    """Simple test user without password hashing"""
    try:
        test_email = f"test{random.randint(1000,9999)}@example.com"
        
        new_user = models.User(
            email=test_email, 
            password="test123"  # Temporary - no hashing
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
        return {"error": str(e)}

@app.get("/test-db")
def test_db(db: Session = Depends(get_db)):
    user_count = db.query(models.User).count()
    return {"database_status": "connected", "total_users": user_count}

@app.get("/test-login")
def test_login(db: Session = Depends(get_db)):
    """Simple login test"""
    user = db.query(models.User).first()
    if not user:
        return {"message": "Pehle /create-test-user par jaake user create karein"}
    
    return {
        "user_exists": True,
        "user_id": user.id,
        "email": user.email,
        "password": user.password  # Show stored password
    }

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=port)
