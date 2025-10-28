from pydantic import BaseModel
from typing import List, Optional
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
