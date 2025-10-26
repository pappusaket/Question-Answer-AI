# schemas.py
from pydantic import BaseModel, EmailStr
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
