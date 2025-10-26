import google.generativeai as genai
from datetime import date
import json
import os

# Gemini AI Setup
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

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
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Daily limit check
    today = date.today()
    activity = db.query(models.UserActivity).filter(
        models.UserActivity.user_id == current_user.id,
        models.UserActivity.subject == request.subject,
        models.UserActivity.last_used_date == today
    ).first()
    
    if activity:
        raise HTTPException(
            status_code=400, 
            detail=f"Daily limit reached for {request.subject}. Try again tomorrow."
        )
    
    # Generate questions (basic implementation)
    questions = generate_sample_questions(request)
    
    # Save activity
    new_activity = models.UserActivity(
        user_id=current_user.id,
        subject=request.subject,
        last_used_date=today,
        questions_generated=len(questions)
    )
    db.add(new_activity)
    
    # Save questions
    for q in questions:
        db_question = models.Question(
            user_id=current_user.id,
            subject=request.subject,
            chapter=request.chapter,
            question_text=q["question"],
            options=json.dumps(q["options"]),
            correct_answer=q["correct_answer"],
            difficulty=request.difficulty,
            language=request.language
        )
        db.add(db_question)
    
    db.commit()
    
    return {"questions": questions, "count": len(questions)}

def generate_sample_questions(request: schemas.QuestionRequest):
    """Sample questions - later Gemini AI se replace karenge"""
    return [
        {
            "question": f"What is the main topic of {request.subject} chapter {request.chapter}?",
            "options": ["Option A", "Option B", "Option C", "Option D"],
            "correct_answer": "Option A"
        }
    ] * 5

@app.get("/user/stats")
def get_user_stats(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
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
