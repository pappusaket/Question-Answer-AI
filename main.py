from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
import os
from database import get_db, engine
import models

# Create tables
models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="Question-AI", version="1.0.0")

@app.get("/")
def home():
    return {"message": "Question AI API is running!", "status": "active"}

@app.get("/health")
def health_check():
    return {"status": "healthy"}

@app.get("/test-db")
def test_db(db: Session = Depends(get_db)):
    try:
        # Simple database test
        user_count = db.query(models.User).count()
        return {"database_status": "connected", "total_users": user_count}
    except Exception as e:
        return {"database_status": "error", "detail": str(e)}

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=port)
