from pydantic import BaseModel, EmailStr
from typing import List, Optional
from datetime import date, datetime

class UserCreate(BaseModel):
    email: EmailStr
    password: str

class UserResponse(BaseModel):
    id: int
    email: EmailStr
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
