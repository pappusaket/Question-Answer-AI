# main.py - COMPLETE WORKING VERSION
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

# Create tables
models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="Question-AI", version="1.0.0")

# Gemini AI Setup
try:
    import google.generativeai as genai
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
    if GEMINI_API_KEY:
        genai.configure(api_key=GEMINI_API_KEY)
        GEMINI_AVAILABLE = True
        print("Gemini AI configured successfully")
    else:
        GEMINI_AVAILABLE = False
        print("GEMINI_API_KEY not found")
except Exception as e:
    GEMINI_AVAILABLE = False
    print(f"Gemini AI setup failed: {e}")

@app.get("/")
def home():
    gemini_status = "available" if GEMINI_AVAILABLE else "unavailable"
    return {
        "message": "Question AI API is running!", 
        "status": "active",
        "gemini_ai": gemini_status
    }

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

# ✅ QUESTION GENERATION
@app.post("/generate-questions")
def generate_questions(
    request: schemas.QuestionRequest,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if GEMINI_AVAILABLE:
        try:
            questions = generate_questions_with_gemini(request)
            source = "Gemini AI"
        except Exception as e:
            questions = generate_sample_questions(request)
            source = f"Sample (AI Error: {str(e)})"
    else:
        questions = generate_sample_questions(request)
        source = "Sample (Gemini AI not configured)"
    
    return {
        "message": f"Questions generated using {source}",
        "subject": request.subject,
        "chapter": request.chapter,
        "questions": questions,
        "count": len(questions)
    }

def generate_questions_with_gemini(request: schemas.QuestionRequest):
    """Gemini AI se actual questions generate karein"""
    try:
        # ✅ CORRECT MODEL NAME - Latest Gemini models
        model = genai.GenerativeModel('gemini-2.0-flash')
        
        prompt = f"""
        Generate 3 unique multiple choice questions for {request.subject} chapter {request.chapter}.
        Difficulty: {request.difficulty}
        Language: {request.language}
        
        Requirements:
        - Each question should be educational and relevant
        - 4 options for each question
        - Mark the correct answer clearly
        
        Return ONLY valid JSON format (no other text):
        [
            {{
                "question": "Question text here?",
                "options": ["Option A", "Option B", "Option C", "Option D"],
                "correct_answer": "Correct option text"
            }}
        ]
        """
        
        response = model.generate_content(prompt)
        print("Gemini Raw Response:", response.text)
        
        # JSON extract karein
        import re
        json_match = re.search(r'\[.*\]', response.text, re.DOTALL)
        if json_match:
            questions = json.loads(json_match.group())
            return questions[:3]  # Maximum 3 questions
        else:
            # Agar JSON parse nahi ho, toh sample return karein
            return generate_sample_questions(request)
            
    except Exception as e:
        print(f"Gemini Error: {e}")
        raise e

def generate_sample_questions(request: schemas.QuestionRequest):
    """Fallback sample questions"""
    sample_data = {
        "physics": [
            {
                "question": "What is Newton's First Law of Motion?",
                "options": ["F = ma", "Action-reaction", "Inertia", "Gravity"],
                "correct_answer": "Inertia"
            },
            {
                "question": "What is the SI unit of force?",
                "options": ["Joule", "Newton", "Watt", "Pascal"],
                "correct_answer": "Newton"
            },
            {
                "question": "What does E=mc² represent?",
                "options": ["Kinetic energy", "Potential energy", "Mass-energy equivalence", "Thermal energy"],
                "correct_answer": "Mass-energy equivalence"
            }
        ],
        "maths": [
            {
                "question": "What is 2 + 2?",
                "options": ["3", "4", "5", "6"],
                "correct_answer": "4"
            },
            {
                "question": "What is the value of π (pi)?",
                "options": ["3.14", "2.71", "1.61", "4.66"],
                "correct_answer": "3.14"
            },
            {
                "question": "What is the area of a circle with radius 2?",
                "options": ["4π", "2π", "π", "8π"],
                "correct_answer": "4π"
            }
        ],
        "chemistry": [
            {
                "question": "What is H₂O?",
                "options": ["Oxygen", "Hydrogen", "Water", "Carbon dioxide"],
                "correct_answer": "Water"
            },
            {
                "question": "What is the atomic number of Carbon?",
                "options": ["6", "8", "12", "14"],
                "correct_answer": "6"
            },
            {
                "question": "What is the chemical symbol for Gold?",
                "options": ["Go", "Gd", "Au", "Ag"],
                "correct_answer": "Au"
            }
        ]
    }
    
    return sample_data.get(request.subject, [
        {
            "question": f"Sample question for {request.subject} chapter {request.chapter}",
            "options": ["Option A", "Option B", "Option C", "Option D"],
            "correct_answer": "Option A"
        }
    ])

# ✅ TEST GEMINI CONNECTION
@app.get("/test-gemini")
def test_gemini():
    """Test Gemini AI connection"""
    if not GEMINI_AVAILABLE:
        return {
            "gemini_status": "not_configured",
            "message": "GEMINI_API_KEY environment variable not set"
        }
    
    try:
        # ✅ CORRECT MODEL NAME - gemini-2.0-flash (fast aur reliable)
        model = genai.GenerativeModel('gemini-2.0-flash')
        response = model.generate_content("Say 'Hello World' in one word.")
        
        return {
            "gemini_status": "connected",
            "model_used": "gemini-2.0-flash",
            "response": response.text,
            "message": "Gemini AI is working successfully!"
        }
    except Exception as e:
        # Alternative model try karein
        try:
            model = genai.GenerativeModel('gemini-2.0-flash-lite')
            response = model.generate_content("Say 'Hello World' in one word.")
            
            return {
                "gemini_status": "connected",
                "model_used": "gemini-2.0-flash-lite", 
                "response": response.text,
                "message": "Gemini AI is working! (using gemini-2.0-flash-lite)"
            }
        except Exception as e2:
            return {
                "gemini_status": "error",
                "error": f"gemini-2.0-flash: {str(e)}, gemini-2.0-flash-lite: {str(e2)}",
                "message": "Both Gemini models failed"
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
