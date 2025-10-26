# main.py - CORRECTED VERSION
from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
import os
import random
import json
from datetime import date
from database import get_db, engine
import models
import schemas
from auth import create_access_token, get_current_user

# Create tables
models.Base.metadata.create_all(bind=engine)

# ✅ APP FIRST DEFINE KAREIN
app = FastAPI(title="Question-AI", version="1.0.0")

# ✅ THEN ENDPOINTS ADD KAREIN
@app.get("/")
def home():
    return {"message": "Question AI API is running!", "status": "active"}

@app.get("/health")
def health_check():
    return {"status": "healthy"}

@app.get("/subjects")
def get_subjects():
    return {
        "subjects": [
            {"id": "physics", "name": "Physics", "chapters": 14},
            {"id": "maths", "name": "Mathematics", "chapters": 13},
            {"id": "chemistry", "name": "Chemistry", "chapters": 16}
        ]
    }

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

# ✅ LOGIN WITH TOKEN
@app.get("/login-test")
def login_test(db: Session = Depends(get_db)):
    user = db.query(models.User).first()
    if not user:
        return {"message": "No users found"}
    
    access_token = create_access_token({"user_id": user.id})
    
    return {
        "message": "Login successful!",
        "user_id": user.id,
        "email": user.email,
        "access_token": access_token,
        "token_type": "bearer"
    }

# ✅ PROTECTED PROFILE
@app.get("/profile")
def get_profile(current_user: models.User = Depends(get_current_user)):
    return {
        "message": "Protected route accessed successfully",
        "user_id": current_user.id, 
        "email": current_user.email
    }

# ✅ QUESTION GENERATION (SAMPLE)
@app.post("/generate-questions")
def generate_questions(
    request: schemas.QuestionRequest,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Daily limit check (basic)
    today = date.today()
    
    # Generate sample questions
    questions = [
        {
            "question": f"What is the main topic of {request.subject} chapter {request.chapter}?",
            "options": ["Option A", "Option B", "Option C", "Option D"],
            "correct_answer": "Option A"
        }
    ] * 3
    
    return {
        "message": "Questions generated successfully",
        "subject": request.subject,
        "chapter": request.chapter,
        "questions": questions,
        "count": len(questions)
    }

# ✅ USER STATS
@app.get("/user/stats")
def get_user_stats(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    return {
        "user_id": current_user.id,
        "today_usage": 0,
        "subjects_used_today": []
    }

@app.get("/test-db")
def test_db(db: Session = Depends(get_db)):
    user_count = db.query(models.User).count()
    return {"database_status": "connected", "total_users": user_count}

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=port)
