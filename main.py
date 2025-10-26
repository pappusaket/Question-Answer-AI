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

# ✅ SIMPLE TEST ENDPOINT - Browser se directly test kar sakte hain
@app.get("/create-test-user")
def create_test_user(db: Session = Depends(get_db)):
    """Test user create karne ke liye simple GET endpoint"""
    test_email = f"test{random.randint(1000,9999)}@example.com"
    
    new_user = models.User(
        email=test_email, 
        password=hash_password("test123")  # Password hash karein
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    return {
        "message": "Test user created successfully", 
        "user_id": new_user.id, 
        "email": test_email,
        "password_used": "test123"
    }

# ✅ SIMPLE LOGIN TEST ENDPOINT  
@app.get("/test-login")
def test_login(db: Session = Depends(get_db)):
    """Test login ke liye - pehle koi user create karein"""
    user = db.query(models.User).first()
    if not user:
        return {"message": "Pehle /create-test-user par jaake user create karein"}
    
    # Verify password
    password_correct = verify_password("test123", user.password)
    
    return {
        "user_exists": True,
        "user_id": user.id,
        "email": user.email,
        "password_verified": password_correct
    }

# ✅ ORIGINAL ENDPOINTS (POST methods - Curl/Postman ke liye)
@app.post("/register")
def register(user_data: schemas.UserCreate, db: Session = Depends(get_db)):
    # Check if user exists
    db_user = db.query(models.User).filter(models.User.email == user_data.email).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Create user with hashed password
    new_user = models.User(
        email=user_data.email,
        password=hash_password(user_data.password)
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    return {"message": "User created successfully", "user_id": new_user.id}

@app.post("/login")
def login(user_data: schemas.UserCreate, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.email == user_data.email).first()
    if not user or not verify_password(user_data.password, user.password):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    access_token = create_access_token({"user_id": user.id})
    return {"access_token": access_token, "token_type": "bearer"}

@app.get("/profile")
def get_profile(current_user: models.User = Depends(get_current_user)):
    return {"user_id": current_user.id, "email": current_user.email}

@app.get("/test-db")
def test_db(db: Session = Depends(get_db)):
    user_count = db.query(models.User).count()
    return {"database_status": "connected", "total_users": user_count}

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=port)
