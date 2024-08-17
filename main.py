import os
from dotenv import load_dotenv
from fastapi import FastAPI, Depends, Request, Form, HTTPException
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.exc import SQLAlchemyError

# Load environment variables
load_dotenv()

# Database connection
SQLALCHEMY_DATABASE_URL = os.getenv("DATABASE_URL")
if not SQLALCHEMY_DATABASE_URL:
    raise ValueError("DATABASE_URL environment variable is not set")

engine = create_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Define a simple model
class Item(Base):
    __tablename__ = "items"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)

# Create the database tables
Base.metadata.create_all(bind=engine)

app = FastAPI()

# Set up Jinja2 templates
templates = Jinja2Templates(directory="templates")

# Mount static files directory
app.mount("/static", StaticFiles(directory="static"), name="static")

# Dependency to get the database session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.get("/")
async def root(request: Request, db: Session = Depends(get_db)):
    items = db.query(Item).all()
    print(f"Items retrieved: {items}")  # Debug print
    return templates.TemplateResponse("index.html", {"request": request, "items": items})

@app.post("/items/")
async def create_item(request: Request, name: str = Form(...), db: Session = Depends(get_db)):
    new_item = Item(name=name)
    db.add(new_item)
    db.commit()
    db.refresh(new_item)
    items = db.query(Item).all()
    return templates.TemplateResponse("index.html", {"request": request, "items": items})

@app.get("/items/{item_id}")
async def read_item(request: Request, item_id: int, db: Session = Depends(get_db)):
    try:
        item = db.query(Item).filter(Item.id == item_id).first()
        if item is None:
            return templates.TemplateResponse("error.html", {"request": request, "error": "Item not found"}, status_code=404)
        return templates.TemplateResponse("item_detail.html", {"request": request, "item": item})
    except SQLAlchemyError as e:
        print(f"Database error: {str(e)}")
        return templates.TemplateResponse("error.html", {"request": request, "error": "Database error occurred"}, status_code=500)
    except Exception as e:
        print(f"Unexpected error: {str(e)}")
        return templates.TemplateResponse("error.html", {"request": request, "error": "An unexpected error occurred"}, status_code=500)