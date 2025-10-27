# main.py - WITH WORDPRESS MEDIA LIBRARY API INTEGRATION

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
import re

from database import get_db, engine
import models
import schemas
from auth import create_access_token, get_current_user

# Create tables
models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="Question-AI", version="2.1.0")

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

# WordPress API Configuration
WORDPRESS_SITE_URL = "https://5minanswer.com"
WORDPRESS_USERNAME = os.getenv("WORDPRESS_USERNAME")
WORDPRESS_PASSWORD = os.getenv("WORDPRESS_PASSWORD")
WORDPRESS_APPLICATION_PASSWORD = os.getenv("WORDPRESS_APPLICATION_PASSWORD")

# ✅ RENDER HEALTH CHECK KE LIYE HEAD ROUTE
@app.head("/")
def head_root():
    return {"message": "OK"}

@app.get("/")
def home():
    gemini_status = "available" if GEMINI_AVAILABLE else "unavailable"
    wordpress_status = "configured" if WORDPRESS_USERNAME and WORDPRESS_APPLICATION_PASSWORD else "not_configured"
    
    return {
        "message": "Question AI API is running!", 
        "status": "active",
        "gemini_ai": gemini_status,
        "wordpress_api": wordpress_status,
        "version": "2.1.0",
        "features": ["daily_limits", "chapter_based", "multi_language", "wordpress_media_api"]
    }

@app.get("/health")
def health_check():
    return {"status": "healthy"}

# ✅ WORDPRESS MEDIA LIBRARY API FUNCTIONS
def get_wordpress_auth_header():
    """WordPress API ke liye authentication header banaye"""
    if WORDPRESS_USERNAME and WORDPRESS_APPLICATION_PASSWORD:
        import base64
        credentials = f"{WORDPRESS_USERNAME}:{WORDPRESS_APPLICATION_PASSWORD}"
        token = base64.b64encode(credentials.encode()).decode()
        return {'Authorization': f'Basic {token}'}
    else:
        return {}

def search_media_files(search_term):
    """WordPress media library mein files search kare"""
    try:
        url = f"{WORDPRESS_SITE_URL}/wp-json/wp/v2/media"
        params = {
            'search': search_term,
            'per_page': 50,
            'orderby': 'date',
            'order': 'desc'
        }
        
        headers = get_wordpress_auth_header()
        response = requests.get(url, params=params, headers=headers, timeout=30)
        
        if response.status_code == 200:
            media_items = response.json()
            return media_items
        else:
            print(f"WordPress API error: {response.status_code} - {response.text}")
            return []
            
    except Exception as e:
        print(f"WordPress search error: {e}")
        return []

def find_chapter_doc(class_level, subject, chapter):
    """Specific chapter ki DOC file find kare"""
    search_terms = [
        f"Class-{class_level}{subject}Chapter-{chapter}",
        f"Class-{class_level}{subject}Chepter-{chapter}",
        f"Class {class_level} {subject} Chapter {chapter}",
        f"Class-{class_level}-{subject}-Chapter-{chapter}",
        f"Class-{class_level}-{subject}-Chepter-{chapter}",
        f"{class_level} {subject} {chapter}",
        f"Class{class_level}{subject}Chapter{chapter}",
    ]
    
    for search_term in search_terms:
        print(f"Searching for: {search_term}")
        media_items = search_media_files(search_term)
        
        for item in media_items:
            file_url = item.get('source_url', '')
            file_title = item.get('title', {}).get('rendered', '')
            file_name = item.get('slug', '')
            
            # Check if this is a DOC file
            if any(ext in file_url.lower() for ext in ['.docx', '.doc']):
                print(f"Found DOC file: {file_title} - {file_url}")
                return file_url
    
    return None

def download_doc_content_from_url(doc_url):
    """DOC file URL se content download kare"""
    try:
        headers = get_wordpress_auth_header()
        response = requests.get(doc_url, headers=headers, timeout=30)
        
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
            print(f"DOC download failed with status: {response.status_code}")
            return None
            
    except Exception as e:
        print(f"DOC download error: {e}")
        return None

def get_doc_content(class_level, subject, chapter):
    """Main function: Chapter ki DOC file find kare aur content return kare"""
    print(f"Looking for Class {class_level} {subject} Chapter {chapter}")
    
    # Step 1: WordPress media library mein search karein
    doc_url = find_chapter_doc(class_level, subject, chapter)
    
    if doc_url:
        # Step 2: DOC file download karein
        content = download_doc_content_from_url(doc_url)
        if content:
            return content
    
    # Step 3: Fallback - Direct URL try karein
    fallback_urls = [
        f"https://5minanswer.com/wp-content/uploads/2025/10/Class-{class_level}{subject.capitalize()}-Chepter-{chapter}.docx",
        f"https://5minanswer.com/wp-content/uploads/2025/10/Class-{class_level}{subject}-Chepter-{chapter}.docx",
        f"https://5minanswer.com/wp-content/uploads/2025/10/Class-{class_level}{subject.capitalize()}-Chapter-{chapter}.docx",
    ]
    
    for url in fallback_urls:
        print(f"Trying fallback URL: {url}")
        content = download_doc_content_from_url(url)
        if content:
            return content
    
    # Step 4: Agar kuch nahi mila, toh AI se directly generate karein
    print("No DOC file found. Using AI fallback.")
    return f"Generate questions for Class {class_level} {subject} Chapter {chapter}"

# ✅ NEW: WORDPRESS MEDIA API TEST ENDPOINT
@app.get("/test-wordpress-media")
def test_wordpress_media():
    """Test WordPress media library connection"""
    if not WORDPRESS_USERNAME or not WORDPRESS_APPLICATION_PASSWORD:
        return {
            "wordpress_status": "not_configured",
            "message": "WORDPRESS_USERNAME and WORDPRESS_APPLICATION_PASSWORD environment variables required"
        }
    
    try:
        # Test search functionality
        media_items = search_media_files("Class-12Physics")
        
        return {
            "wordpress_status": "connected",
            "media_items_found": len(media_items),
            "sample_items": [
                {
                    "id": item.get('id'),
                    "title": item.get('title', {}).get('rendered'),
                    "url": item.get('source_url'),
                    "type": item.get('mime_type')
                }
                for item in media_items[:3]  # First 3 items
            ],
            "message": "WordPress media library accessible"
        }
    except Exception as e:
        return {
            "wordpress_status": "error",
            "error": str(e),
            "message": "WordPress media library connection failed"
        }

# ✅ NEW: SEARCH MEDIA FILES ENDPOINT
@app.get("/search-media")
def search_media_files_endpoint(search_term: str = ""):
    """WordPress media library mein files search kare"""
    if not search_term:
        return {"error": "Search term required"}
    
    media_items = search_media_files(search_term)
    
    return {
        "search_term": search_term,
        "total_found": len(media_items),
        "media_files": [
            {
                "id": item.get('id'),
                "title": item.get('title', {}).get('rendered'),
                "url": item.get('source_url'),
                "mime_type": item.get('mime_type'),
                "date": item.get('date')
            }
            for item in media_items
        ]
    }

# ✅ AVAILABLE SUBJECTS AND CHAPTERS
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

# ✅ DAILY LIMIT CHECKER
def check_daily_limit(db: Session, user_id: int, subject: str):
    """24 hours ka limit check karega"""
    today = date.today()
    
    usage = db.query(models.UsageLimit).filter(
        models.UsageLimit.user_id == user_id,
        models.UsageLimit.subject == subject,
        models.UsageLimit.last_used_date == today
    ).first()
    
    if usage:
        if usage.questions_generated_today >= 25:
            return False, "Daily limit reached for this subject. You can generate 25 questions per subject every 24 hours."
        # Increment count
        usage.questions_generated_today += 1
    else:
        # New entry
        usage = models.UsageLimit(
            user_id=user_id,
            subject=subject,
            last_used_date=today,
            questions_generated_today=1
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

# ✅ SMART QUESTION GENERATOR FROM DOC CONTENT
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

# ✅ GENERATE FROM CHAPTER ENDPOINT (UPDATED)
@app.post("/generate-from-chapter")
def generate_from_chapter(
    request: schemas.ChapterRequest,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # 1. Daily limit check
    limit_ok, message = check_daily_limit(db, current_user.id, request.subject)
    if not limit_ok:
        raise HTTPException(status_code=400, detail=message)
    
    # 2. Get DOC content from WordPress media library
    content = get_doc_content(request.class_level, request.subject, request.chapter)
    
    # 3. Generate questions
    questions = generate_questions_from_content(
        content, 
        request.question_count, 
        request.difficulty, 
        request.language
    )
    
    # 4. Save to history
    for q in questions:
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
    db.commit()
    
    # 5. Determine content source
    content_source = "WordPress DOC File" if "Generate questions for" not in content else "AI Generation (No DOC)"
    
    return {
        "message": "Questions generated successfully",
        "content_source": content_source,
        "class_level": request.class_level,
        "subject": request.subject,
        "chapter": request.chapter,
        "difficulty": request.difficulty,
        "language": request.language,
        "questions_generated": len(questions),
        "daily_remaining": 25 - get_today_usage(db, current_user.id, request.subject),
        "questions": questions
    }

# ✅ MY USAGE STATUS
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

@app.get("/test-db")
def test_db(db: Session = Depends(get_db)):
    user_count = db.query(models.User).count()
    return {"database_status": "connected", "total_users": user_count}

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=port)
