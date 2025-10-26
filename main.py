from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from datetime import datetime, date
import google.generativeai as genai
import requests
from docx import Document
import os
from dotenv import load_dotenv

from database import get_db, engine
import models
import schemas
from auth import create_access_token, verify_token, get_current_user

load_dotenv()

app = FastAPI(title="Question-Answer-AI", version="1.0.0")

# CORS setup
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Gemini AI setup
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

security = HTTPBearer()

# Create tables
models.Base.metadata.create_all(bind=engine)

@app.post("/register", response_model=schemas.UserResponse)
def register(user_data: schemas.UserCreate, db: Session = Depends(get_db)):
    # Check if user already exists
    db_user = db.query(models.User).filter(models.User.email == user_data.email).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Create new user
    new_user = models.User(
        email=user_data.email,
        password=user_data.password  # In production, hash this password
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    return new_user

@app.post("/login")
def login(user_data: schemas.UserCreate, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.email == user_data.email).first()
    if not user or user.password != user_data.password:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    access_token = create_access_token(data={"user_id": user.id})
    return {"access_token": access_token, "token_type": "bearer"}

@app.get("/subjects")
def get_subjects():
    return {
        "subjects": [
            {"id": "physics", "name": "Physics", "chapters": 14},
            {"id": "maths", "name": "Mathematics", "chapters": 13},
            {"id": "chemistry", "name": "Chemistry", "chapters": 16}
        ]
    }

@app.post("/generate-questions")
def generate_questions(
    request: schemas.QuestionRequest,
    current_user: schemas.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Check daily limit
    today = date.today()
    activity = db.query(models.UserActivity).filter(
        models.UserActivity.user_id == current_user.id,
        models.UserActivity.subject == request.subject,
        models.UserActivity.last_used_date == today
    ).first()
    
    if activity:
        raise HTTPException(
            status_code=400, 
            detail=f"You have already generated questions for {request.subject} today. Try again tomorrow."
        )
    
    # Get document from WordPress
    doc_content = get_document_content(request.subject, request.chapter)
    
    # Generate questions using Gemini AI
    questions = generate_questions_with_gemini(
        doc_content, 
        request.subject, 
        request.chapter, 
        request.difficulty, 
        request.language
    )
    
    # Save activity
    new_activity = models.UserActivity(
        user_id=current_user.id,
        subject=request.subject,
        last_used_date=today,
        questions_generated=25
    )
    db.add(new_activity)
    
    # Save questions
    for q in questions:
        db_question = models.Question(
            subject=request.subject,
            chapter=request.chapter,
            question_text=q["question"],
            options=q["options"],
            correct_answer=q["correct_answer"],
            difficulty=request.difficulty,
            language=request.language
        )
        db.add(db_question)
    
    db.commit()
    
    return {"questions": questions, "count": len(questions)}

def get_document_content(subject: str, chapter: int) -> str:
    """Fetch and parse document from WordPress media library"""
    # WordPress API endpoint (aapko ye URL update karna hoga)
    wp_api_url = f"https://your-wordpress-site.com/wp-json/wp/v2/media"
    
    try:
        # Yahan aapko actual WordPress integration implement karna hoga
        # For now, return sample content
        return f"Sample content for {subject} chapter {chapter}"
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching document: {str(e)}")

def generate_questions_with_gemini(content: str, subject: str, chapter: int, difficulty: str, language: str) -> list:
    """Generate questions using Gemini AI"""
    
    prompt = f"""
    Generate 25 one-liner multiple choice questions from the following content:
    Subject: {subject}
    Chapter: {chapter}
    Difficulty: {difficulty}
    Language: {language}
    
    Content: {content[:2000]}  # Limit content length
    
    Requirements:
    - Create 25 one-liner questions
    - Each question should have 4 options (1 correct, 3 wrong)
    - Questions should be in {language}
    - Difficulty level: {difficulty}
    - Return in JSON format:
    [
        {{
            "question": "question text",
            "options": ["option1", "option2", "option3", "option4"],
            "correct_answer": "correct option text"
        }}
    ]
    """
    
    try:
        model = genai.GenerativeModel('gemini-pro')
        response = model.generate_content(prompt)
        
        # Parse response and return questions
        # Note: Actual parsing logic depends on Gemini's response format
        questions = parse_gemini_response(response.text)
        return questions[:25]  # Ensure only 25 questions
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI question generation failed: {str(e)}")

def parse_gemini_response(response_text: str) -> list:
    """Parse Gemini AI response to extract questions"""
    # Yahan aapko actual parsing logic implement karni hogi
    # For now, return sample questions
    return [
        {
            "question": "What is the formula for force?",
            "options": ["F = ma", "F = mv", "F = mgh", "F = pV"],
            "correct_answer": "F = ma"
        }
    ] * 25

@app.get("/user/stats")
def get_user_stats(
    current_user: schemas.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get user's daily usage statistics"""
    today = date.today()
    today_activities = db.query(models.UserActivity).filter(
        models.UserActivity.user_id == current_user.id,
        models.UserActivity.last_used_date == today
    ).all()
    
    return {
        "user_id": current_user.id,
        "today_usage": len(today_activities),
        "subjects_used_today": [act.subject for act in today_activities]
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
