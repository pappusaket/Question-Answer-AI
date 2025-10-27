# main.py - WITH TOKEN MANAGEMENT ENDPOINTS
from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
import os
import random
import json
import traceback
from datetime import date, datetime
from database import get_db, engine
import models
import schemas
from auth import create_access_token, get_current_user, get_token_info, verify_token

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

# ✅ CORRECT MODEL NAMES
GEMINI_MODELS = [
    'models/gemini-2.0-flash',
    'models/gemini-2.0-flash-001', 
    'models/gemini-pro-latest',
    'models/gemini-flash-latest'
]

@app.get("/")
def home():
    gemini_status = "available" if GEMINI_AVAILABLE else "unavailable"
    return {
        "message": "Question AI API is running!", 
        "status": "active",
        "gemini_ai": gemini_status,
        "features": ["Authentication", "Question Generation", "Token Management"]
    }

# ✅ TOKEN MANAGEMENT ENDPOINTS
@app.get("/token/info")
def get_token_info_endpoint(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Current token ki information provide karein
    """
    from fastapi import Request
    from fastapi.security import HTTPBearer
    
    # Token extract karein
    security = HTTPBearer()
    credentials = security(request=Request)
    token = credentials.credentials
    
    token_info = get_token_info(token)
    
    return {
        "user_id": current_user.id,
        "email": current_user.email,
        "token_info": token_info
    }

@app.post("/token/refresh")
def refresh_token(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    New token generate karein (existing user ke liye)
    """
    new_token = create_access_token({"user_id": current_user.id})
    
    return {
        "message": "Token refreshed successfully",
        "access_token": new_token,
        "token_type": "bearer",
        "user_id": current_user.id
    }

@app.get("/token/validate")
def validate_token(
    current_user: models.User = Depends(get_current_user)
):
    """
    Simple token validation endpoint
    """
    return {
        "valid": True,
        "message": "Token is valid",
        "user_id": current_user.id,
        "email": current_user.email
    }

# Existing endpoints remain the same...
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

@app.get("/create-test-user")
def create_test_user(db: Session = Depends(get_db)):
    test_email = f"test{random.randint(1000,9999)}@example.com"
    
    new_user = models.User(email=test_email, password="test123")
    db.add(new_user)
    db.commit()
    
    # Automatically token bhi return karein
    access_token = create_access_token({"user_id": new_user.id})
    
    return {
        "message": "Test user created successfully", 
        "user_id": new_user.id, 
        "email": test_email,
        "access_token": access_token,
        "token_type": "bearer"
    }

@app.get("/login-test")
def login_test(db: Session = Depends(get_db)):
    user = db.query(models.User).first()
    if not user:
        return {"message": "No users found"}
    
    access_token = create_access_token({"user_id": user.id})
    token_info = get_token_info(access_token)
    
    return {
        "message": "Login successful!",
        "user_id": user.id,
        "email": user.email,
        "access_token": access_token,
        "token_type": "bearer",
        "token_expires": token_info.get("expires_at"),
        "days_remaining": token_info.get("days_remaining")
    }

@app.get("/profile")
def get_profile(current_user: models.User = Depends(get_current_user)):
    return {
        "message": "Protected route accessed successfully",
        "user_id": current_user.id, 
        "email": current_user.email
    }

# Question generation endpoints...
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
    for model_name in GEMINI_MODELS:
        try:
            model = genai.GenerativeModel(model_name)
            
            prompt = f"""
            Generate 3 unique multiple choice questions for {request.subject} chapter {request.chapter}.
            Return ONLY valid JSON format.
            """
            
            response = model.generate_content(prompt)
            
            import re
            json_match = re.search(r'\[.*\]', response.text, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
                
        except Exception:
            continue
    
    return generate_sample_questions(request)

def generate_sample_questions(request: schemas.QuestionRequest):
    sample_data = {
        "physics": [
            {
                "question": "What is Newton's First Law of Motion?",
                "options": ["F = ma", "Action-reaction", "Inertia", "Gravity"],
                "correct_answer": "Inertia"
            }
        ],
        "maths": [
            {
                "question": "What is 2 + 2?",
                "options": ["3", "4", "5", "6"],
                "correct_answer": "4"
            }
        ],
        "chemistry": [
            {
                "question": "What is H₂O?",
                "options": ["Oxygen", "Hydrogen", "Water", "Carbon dioxide"],
                "correct_answer": "Water"
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

@app.get("/test-gemini")
def test_gemini():
    if not GEMINI_AVAILABLE:
        return {"gemini_status": "not_configured"}
    
    for model_name in GEMINI_MODELS:
        try:
            model = genai.GenerativeModel(model_name)
            response = model.generate_content("Say 'Hello World' in one word.")
            
            return {
                "gemini_status": "connected",
                "model_used": model_name,
                "response": response.text
            }
        except Exception:
            continue
    
    return {"gemini_status": "error"}

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
