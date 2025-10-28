# main.py - COMPLETE UPDATED VERSION WITH QUIZ SYSTEM 

from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
import os
import random
import json
import traceback
from datetime import date, datetime
import requests
from docx import Document
import io

from database import get_db, engine
import models
import schemas
from auth import create_access_token, get_current_user

# Create tables
models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="Question-AI", version="3.0.0")

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

# ✅ RENDER HEALTH CHECK KE LIYE HEAD ROUTE
@app.head("/")
def head_root():
    return {"message": "OK"}

@app.get("/")
def home():
    gemini_status = "available" if GEMINI_AVAILABLE else "unavailable"
    return {
        "message": "Question AI API is running!", 
        "status": "active",
        "gemini_ai": gemini_status,
        "version": "3.0.0",
        "features": ["daily_limits", "chapter_based", "multi_language", "quiz_system"]
    }

@app.get("/health")
def health_check():
    return {"status": "healthy"}

# ✅ NEW: AVAILABLE SUBJECTS AND CHAPTERS
@app.get("/available-subjects")
def get_available_subjects():
    return {
        "classes": [9, 10, 11, 12],
        "subjects": [
            {"id": "physics", "name": "Physics", "chapters": 14},
            {"id": "maths", "name": "Mathematics", "chapters": 13},
            {"id": "chemistry", "name": "Chemistry", "chapters": 16},
            {"id": "hindi", "name": "Hindi", "chapters": 10},
            {"id": "english", "name": "English", "chapters": 8},
            {"id": "social-science", "name": "Social Science", "chapters": 12},
            {"id": "sanskrit", "name": "Sanskrit", "chapters": 6}
        ]
    }

# ✅ NEW: DOWNLOAD DOC CONTENT FROM WORDPRESS
def download_doc_content(class_level, subject, chapter):
    """WordPress se DOC file download karke text extract karega"""
    try:
        # URL format based on your WordPress site
        subject_formatted = subject.capitalize()
        url = f"https://5minanswer.com/wp-content/uploads/2025/10/Class-{class_level}{subject_formatted}-Chapter-{chapter}.docx"
        
        print(f"Downloading from: {url}")
        response = requests.get(url, timeout=30)
        
        if response.status_code == 200:
            # DOC file parse karein
            doc = Document(io.BytesIO(response.content))
            content = ""
            for paragraph in doc.paragraphs:
                if paragraph.text.strip():
                    content += paragraph.text + "\n"
            
            print(f"Downloaded content length: {len(content)}")
            return content if content else None
        else:
            print(f"Download failed with status: {response.status_code}")
            return None
            
    except Exception as e:
        print(f"DOC download error: {e}")
        return None

# ✅ FIXED: DAILY LIMIT CHECKER
def check_daily_limit(db: Session, user_id: int, subject: str, requested_count: int):
    """24 hours ka limit check karega - FIXED VERSION"""
    today = date.today()
    
    usage = db.query(models.UsageLimit).filter(
        models.UsageLimit.user_id == user_id,
        models.UsageLimit.subject == subject,
        models.UsageLimit.last_used_date == today
    ).first()
    
    if usage:
        # ✅ FIXED: requested_count se compare karega
        if usage.questions_generated_today + requested_count > 25:
            return False, f"Aaj ki limit poori ho gayi! Aap {usage.questions_generated_today}/25 questions generate kar chuke hain. Kal fir se try karein."
        
        # ✅ FIXED: requested_count se update karega
        usage.questions_generated_today += requested_count
    else:
        # ✅ FIXED: new entry mein requested_count set karega
        if requested_count > 25:
            return False, "Aap 25 questions se zyada nahi generate kar sakte."
        
        usage = models.UsageLimit(
            user_id=user_id,
            subject=subject,
            last_used_date=today,
            questions_generated_today=requested_count  # ✅ FIXED
        )
        db.add(usage)
    
    db.commit()
    return True, "Limit check passed"

def get_today_usage(db: Session, user_id: int, subject: str):
    """Get today's usage for a subject"""
    today = date.today()
    usage = db.query(models.UsageLimit).filter(
        models.UsageLimit.user_id == user_id,
        models.UsageLimit.subject == subject,
        models.UsageLimit.last_used_date == today
    ).first()
    
    return usage.questions_generated_today if usage else 0

# ✅ NEW: SMART QUESTION GENERATOR FROM DOC CONTENT
def generate_questions_from_content(content, question_count=25, difficulty="medium", language="english"):
    """DOC content se intelligent questions generate karega"""
    if not GEMINI_AVAILABLE:
        return generate_sample_questions_from_subject("general", question_count)
    
    try:
        model = genai.GenerativeModel('gemini-2.0-flash')
        
        prompt = f"""
        Based on the following textbook chapter content, generate {question_count} multiple choice questions.
        
        CONTENT:
        {content[:3000]}  # Limit content length
        
        Requirements:
        - Create one-line objective questions
        - 4 options for each question (1 correct + 3 wrong)
        - Difficulty: {difficulty}
        - Language: {language}
        - Questions should be based on the actual content
        - Wrong options should be plausible but incorrect
        - Return exactly {question_count} questions
        
        Return ONLY valid JSON format (no other text):
        [
            {{
                "question": "One-line question text?",
                "options": ["Option A", "Option B", "Option C", "Option D"],
                "correct_answer": "Correct option text"
            }}
        ]
        """
        
        response = model.generate_content(prompt)
        print("Gemini Response:", response.text)
        
        # JSON extract karein
        import re
        json_match = re.search(r'\[.*\]', response.text, re.DOTALL)
        if json_match:
            questions = json.loads(json_match.group())
            return questions[:question_count]
        else:
            return generate_sample_questions_from_subject("general", question_count)
            
    except Exception as e:
        print(f"Gemini Error: {e}")
        return generate_sample_questions_from_subject("general", question_count)

def generate_sample_questions_from_subject(subject, count=25):
    """Fallback sample questions"""
    sample_questions = []
    for i in range(count):
        sample_questions.append({
            "question": f"Sample question {i+1} for {subject}?",
            "options": [f"Option A", f"Option B", f"Option C", f"Option D"],
            "correct_answer": f"Option A"
        })
    return sample_questions

# ✅ NEW: GENERATE FROM CHAPTER ENDPOINT
@app.post("/generate-from-chapter")
def generate_from_chapter(
    request: schemas.ChapterRequest,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # 1. Daily limit check - FIXED CALL
    limit_ok, message = check_daily_limit(db, current_user.id, request.subject, request.question_count)
    if not limit_ok:
        raise HTTPException(status_code=400, detail=message)
    
    # 2. Download DOC content
    content = download_doc_content(request.class_level, request.subject, request.chapter)
    if not content:
        # Fallback to AI without content
        content = f"Generate {request.question_count} questions for Class {request.class_level} {request.subject} Chapter {request.chapter}"
    
    # 3. Generate questions
    questions = generate_questions_from_content(
        content, 
        request.question_count, 
        request.difficulty, 
        request.language
    )
    
    # 4. Save to history with unique IDs for quiz system
    saved_questions = []
    for i, q in enumerate(questions):
        history = models.QuestionHistory(
            user_id=current_user.id,
            class_level=request.class_level,
            subject=request.subject,
            chapter=request.chapter,
            question_text=q["question"],
            options=json.dumps(q["options"]),
            correct_answer=q["correct_answer"],
            difficulty=request.difficulty,
            language=request.language
        )
        db.add(history)
        db.flush()  # Get the ID
        saved_questions.append({
            "id": history.id,
            "question": q["question"],
            "options": q["options"],
            "correct_answer": q["correct_answer"]
        })
    
    db.commit()
    
    return {
        "message": "Questions generated successfully",
        "class_level": request.class_level,
        "subject": request.subject,
        "chapter": request.chapter,
        "difficulty": request.difficulty,
        "language": request.language,
        "questions_generated": len(questions),
        "daily_remaining": 25 - get_today_usage(db, current_user.id, request.subject),
        "questions": saved_questions  # Now includes IDs for quiz
    }

# ✅ NEW: QUIZ SUBMISSION ENDPOINT
@app.post("/submit-quiz")
def submit_quiz(
    request: schemas.QuizSubmission,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    try:
        # Calculate results
        correct_count = 0
        detailed_results = []
        
        for answer in request.answers:
            # Find the original question
            original_question = None
            for q in request.questions:
                if q.get('id') == answer.question_id:
                    original_question = q
                    break
            
            if not original_question:
                continue
            
            is_correct = (answer.selected_answer == original_question['correct_answer'])
            if is_correct:
                correct_count += 1
            
            detailed_results.append({
                "question_id": answer.question_id,
                "question_text": original_question['question'],
                "options": original_question['options'],
                "selected_answer": answer.selected_answer,
                "correct_answer": original_question['correct_answer'],
                "is_correct": is_correct
            })
        
        total_questions = len(request.answers)
        score_percentage = (correct_count / total_questions) * 100 if total_questions > 0 else 0
        
        # Save quiz attempt
        quiz_attempt = models.QuizAttempt(
            user_id=current_user.id,
            class_level=request.class_level,
            subject=request.subject,
            chapter=request.chapter,
            total_questions=total_questions,
            correct_answers=correct_count,
            score_percentage=score_percentage,
            time_taken=request.time_taken
        )
        db.add(quiz_attempt)
        db.flush()  # Get the quiz ID
        
        # Save student responses
        for result in detailed_results:
            response = models.StudentResponse(
                user_id=current_user.id,
                quiz_attempt_id=quiz_attempt.id,
                question_id=result["question_id"],
                question_text=result["question_text"],
                selected_answer=result["selected_answer"],
                correct_answer=result["correct_answer"],
                is_correct=1 if result["is_correct"] else 0,
                options=json.dumps(result["options"])
            )
            db.add(response)
        
        db.commit()
        
        return {
            "quiz_id": quiz_attempt.id,
            "total_questions": total_questions,
            "correct_answers": correct_count,
            "wrong_answers": total_questions - correct_count,
            "score_percentage": round(score_percentage, 2),
            "time_taken": request.time_taken,
            "subject": request.subject,
            "chapter": request.chapter,
            "class_level": request.class_level,
            "attempted_at": quiz_attempt.attempted_at.isoformat(),
            "detailed_results": detailed_results
        }
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Quiz submission failed: {str(e)}")

# ✅ NEW: PERFORMANCE HISTORY ENDPOINT
@app.get("/performance-history")
def get_performance_history(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    attempts = db.query(models.QuizAttempt).filter(
        models.QuizAttempt.user_id == current_user.id
    ).order_by(models.QuizAttempt.attempted_at.desc()).limit(20).all()
    
    history = []
    for attempt in attempts:
        history.append({
            "quiz_id": attempt.id,
            "subject": attempt.subject,
            "chapter": attempt.chapter,
            "score_percentage": attempt.score_percentage,
            "correct_answers": attempt.correct_answers,
            "total_questions": attempt.total_questions,
            "attempted_at": attempt.attempted_at.isoformat()
        })
    
    # Calculate overall stats
    total_attempts = len(attempts)
    if total_attempts > 0:
        avg_score = sum([a.score_percentage for a in attempts]) / total_attempts
        best_score = max([a.score_percentage for a in attempts])
        worst_score = min([a.score_percentage for a in attempts])
    else:
        avg_score = best_score = worst_score = 0
    
    return {
        "user_id": current_user.id,
        "total_attempts": total_attempts,
        "average_score": round(avg_score, 2),
        "best_score": round(best_score, 2),
        "worst_score": round(worst_score, 2),
        "history": history
    }

# ✅ NEW: QUIZ DETAILS ENDPOINT
@app.get("/quiz-details/{quiz_id}")
def get_quiz_details(
    quiz_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Get quiz attempt
    quiz_attempt = db.query(models.QuizAttempt).filter(
        models.QuizAttempt.id == quiz_id,
        models.QuizAttempt.user_id == current_user.id
    ).first()
    
    if not quiz_attempt:
        raise HTTPException(status_code=404, detail="Quiz not found")
    
    # Get detailed responses
    responses = db.query(models.StudentResponse).filter(
        models.StudentResponse.quiz_attempt_id == quiz_id
    ).all()
    
    detailed_results = []
    for response in responses:
        detailed_results.append({
            "question_id": response.question_id,
            "question_text": response.question_text,
            "options": json.loads(response.options),
            "selected_answer": response.selected_answer,
            "correct_answer": response.correct_answer,
            "is_correct": bool(response.is_correct)
        })
    
    return {
        "quiz_id": quiz_attempt.id,
        "subject": quiz_attempt.subject,
        "chapter": quiz_attempt.chapter,
        "class_level": quiz_attempt.class_level,
        "total_questions": quiz_attempt.total_questions,
        "correct_answers": quiz_attempt.correct_answers,
        "score_percentage": quiz_attempt.score_percentage,
        "time_taken": quiz_attempt.time_taken,
        "attempted_at": quiz_attempt.attempted_at.isoformat(),
        "detailed_results": detailed_results
    }

# ✅ NEW: MY USAGE STATUS
@app.get("/my-usage")
def get_my_usage(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    today = date.today()
    
    usage = db.query(models.UsageLimit).filter(
        models.UsageLimit.user_id == current_user.id,
        models.UsageLimit.last_used_date == today
    ).all()
    
    subjects_used = []
    for u in usage:
        subjects_used.append({
            "subject": u.subject,
            "questions_generated": u.questions_generated_today,
            "remaining": 25 - u.questions_generated_today
        })
    
    return {
        "user_id": current_user.id,
        "date": today.isoformat(),
        "daily_limit": 25,
        "subjects_used": subjects_used
    }

# ✅ OLD ROUTES (FOR BACKWARD COMPATIBILITY)
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

# ✅ OLD QUESTION GENERATION (FOR BACKWARD COMPATIBILITY)
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
        model = genai.GenerativeModel('gemini-2.0-flash')
        response = model.generate_content("Say 'Hello World' in one word.")
        
        return {
            "gemini_status": "connected",
            "model_used": "gemini-2.0-flash",
            "response": response.text,
            "message": "Gemini AI is working successfully!"
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
