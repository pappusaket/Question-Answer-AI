# main.py - WITH GEMINI AI
from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
import os
import random
import json
import traceback
from datetime import date
from database import get_db, engine
import models
import schemas
from auth import create_access_token, get_current_user
import google.generativeai as genai

# Create tables
models.Base.metadata.create_all(bind=engine)

# Gemini AI Setup
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

app = FastAPI(title="Question-AI", version="1.0.0")

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

# ✅ GEMINI AI QUESTION GENERATION
@app.post("/generate-questions")
def generate_questions(
    request: schemas.QuestionRequest,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    try:
        # Try Gemini AI first
        questions = generate_questions_with_gemini(request)
        source = "Gemini AI"
        
    except Exception as e:
        # Fallback to sample questions
        questions = generate_sample_questions(request)
        source = f"Sample (AI Error: {str(e)})"
    
    return {
        "message": f"Questions generated successfully using {source}",
        "subject": request.subject,
        "chapter": request.chapter,
        "difficulty": request.difficulty,
        "questions": questions,
        "count": len(questions)
    }

def generate_questions_with_gemini(request: schemas.QuestionRequest):
    """Gemini AI se actual questions generate karein"""
    try:
        model = genai.GenerativeModel('gemini-pro')
        
        prompt = f"""
        Generate 3 unique multiple choice questions for {request.subject} chapter {request.chapter}.
        Difficulty level: {request.difficulty}
        Language: {request.language}
        
        Each question should have:
        - Clear question text
        - 4 options (A, B, C, D)
        - Correct answer marked
        
        Return ONLY valid JSON format like this:
        [
            {{
                "question": "What is Newton's First Law?",
                "options": ["F=ma", "Action-reaction", "Inertia", "Gravity"],
                "correct_answer": "Inertia"
            }}
        ]
        
        Make questions relevant to {request.subject} chapter {request.chapter}.
        """
        
        response = model.generate_content(prompt)
        print("Gemini Response:", response.text)  # Debugging
        
        # Simple parsing - extract JSON from response
        import re
        json_match = re.search(r'\[.*\]', response.text, re.DOTALL)
        if json_match:
            questions = json.loads(json_match.group())
            return questions
        else:
            raise Exception("Could not parse Gemini response")
            
    except Exception as e:
        print(f"Gemini AI Error: {str(e)}")
        raise e

def generate_sample_questions(request: schemas.QuestionRequest):
    """Fallback sample questions"""
    sample_questions = {
        "physics": [
            {
                "question": "What is Newton's First Law of Motion?",
                "options": ["F = ma", "Every action has equal reaction", "Object at rest stays at rest", "Energy conservation"],
                "correct_answer": "Object at rest stays at rest"
            },
            {
                "question": "What is the SI unit of force?",
                "options": ["Joule", "Newton", "Watt", "Pascal"],
                "correct_answer": "Newton"
            }
        ],
        "maths": [
            {
                "question": "What is the value of π (pi)?",
                "options": ["3.14", "2.71", "1.61", "4.66"],
                "correct_answer": "3.14"
            }
        ],
        "chemistry": [
            {
                "question": "What is the atomic number of Hydrogen?",
                "options": ["1", "2", "6", "8"],
                "correct_answer": "1"
            }
        ]
    }
    
    return sample_questions.get(request.subject, [
        {
            "question": f"Sample question for {request.subject} chapter {request.chapter}",
            "options": ["Option A", "Option B", "Option C", "Option D"],
            "correct_answer": "Option A"
        }
    ])

# ✅ TEST GEMINI CONNECTION (Public endpoint)
@app.get("/test-gemini")
def test_gemini():
    """Test Gemini AI connection without authentication"""
    try:
        model = genai.GenerativeModel('gemini-pro')
        response = model.generate_content("Say 'Hello World' in one word.")
        
        return {
            "gemini_status": "connected",
            "response": response.text,
            "message": "Gemini AI is working correctly!"
        }
    except Exception as e:
        return {
            "gemini_status": "error",
            "error": str(e),
            "message": "Gemini AI connection failed"
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
