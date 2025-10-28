from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime

class UserCreate(BaseModel):
    email: str
    password: str

class UserResponse(BaseModel):
    id: int
    email: str
    created_at: datetime
    
    class Config:
        from_attributes = True

class QuestionRequest(BaseModel):
    subject: str
    chapter: int
    difficulty: str = "medium"
    language: str = "english"

class QuestionResponse(BaseModel):
    question: str
    options: List[str]
    correct_answer: str

class UserStats(BaseModel):
    user_id: int
    today_usage: int
    subjects_used_today: List[str]

# NEW SCHEMAS FOR CHAPTER-BASED QUESTIONS
class ChapterRequest(BaseModel):
    class_level: int
    subject: str
    chapter: int
    difficulty: str = "medium"
    language: str = "english"
    question_count: int = 25

class SubjectInfo(BaseModel):
    id: str
    name: str
    chapters: int

class AvailableSubjectsResponse(BaseModel):
    classes: List[int]
    subjects: List[SubjectInfo]

class UsageStatus(BaseModel):
    subject: str
    questions_generated: int
    remaining: int

class MyUsageResponse(BaseModel):
    user_id: int
    date: str
    subjects_used: List[UsageStatus]

# NEW SCHEMAS FOR QUIZ SYSTEM
class StudentAnswer(BaseModel):
    question_id: int
    selected_answer: str

class QuizSubmission(BaseModel):
    class_level: int
    subject: str
    chapter: int
    questions: List[Dict[str, Any]]  # Original questions with IDs
    answers: List[StudentAnswer]
    time_taken: int = 0

class QuizResult(BaseModel):
    quiz_id: int
    total_questions: int
    correct_answers: int
    wrong_answers: int
    score_percentage: float
    time_taken: int
    subject: str
    chapter: int
    class_level: int
    attempted_at: datetime

class PerformanceHistory(BaseModel):
    quiz_id: int
    subject: str
    chapter: int
    score_percentage: float
    correct_answers: int
    total_questions: int
    attempted_at: datetime

class DetailedResult(BaseModel):
    question: str
    options: List[str]
    selected_answer: str
    correct_answer: str
    is_correct: bool
