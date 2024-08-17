import os
from dotenv import load_dotenv
from fastapi import FastAPI, Depends, Request, Form, HTTPException
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
from fastapi.middleware.httpsredirect import HTTPSRedirectMiddleware
from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.exc import SQLAlchemyError

# Load environment variables from .env file (will be ignored if file doesn't exist)
load_dotenv()


#### CODE TO DIFFERENTIATE PROD VS. LOCAL DATABASE SETTINGS
# Get the DATABASE_URL from environment variables
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./test.db")

# If the URL starts with postgres://, replace it with postgresql://
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)
#### NEW CODE ENDS





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

    def __repr__(self):
        return f"<Item(id={self.id}, name='{self.name}')>"

# Create the database tables
Base.metadata.create_all(bind=engine)

app = FastAPI()

# enforce HTTPS
app.add_middleware(HTTPSRedirectMiddleware)

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
    try:
        items = db.query(Item).all()
        print(f"Items retrieved: {items}")  # Debug print
        return templates.TemplateResponse("index.html", {"request": request, "items": items})
    except Exception as e:
        print(f"Error in root: {str(e)}")
        return templates.TemplateResponse("error.html", {"request": request, "error": str(e)})

@app.post("/items/")
async def create_item(request: Request, name: str = Form(...), db: Session = Depends(get_db)):
    try:
        new_item = Item(name=name)
        db.add(new_item)
        db.commit()
        db.refresh(new_item)
        print(f"New item created: {new_item}")  # Debug print
        return RedirectResponse(url="/", status_code=303)
    except Exception as e:
        print(f"Error in create_item: {str(e)}")
        return templates.TemplateResponse("error.html", {"request": request, "error": str(e)})

@app.get("/items/{item_id}")
async def read_item(request: Request, item_id: int, db: Session = Depends(get_db)):
    try:
        item = db.query(Item).filter(Item.id == item_id).first()
        print(f"Retrieved item: {item}")  # Debug print
        if item is None:
            print(f"Item not found: id={item_id}")  # Debug print
            return templates.TemplateResponse("error.html", {"request": request, "error": "Item not found"}, status_code=404)
        print(f"Rendering item_detail.html for item: {item}")  # Debug print
        return templates.TemplateResponse("item_detail.html", {"request": request, "item": item})
    except SQLAlchemyError as e:
        print(f"Database error in read_item: {str(e)}")
        return templates.TemplateResponse("error.html", {"request": request, "error": "Database error occurred"}, status_code=500)
    except Exception as e:
        print(f"Unexpected error in read_item: {str(e)}")
        return templates.TemplateResponse("error.html", {"request": request, "error": "An unexpected error occurred"}, status_code=500)

@app.post("/items/{item_id}/delete")
async def delete_item(request: Request, item_id: int, db: Session = Depends(get_db)):
    try:
        item = db.query(Item).filter(Item.id == item_id).first()
        if item is None:
            return templates.TemplateResponse("error.html", {"request": request, "error": "Item not found"}, status_code=404)
        db.delete(item)
        db.commit()
        print(f"Item deleted: {item}")  # Debug print
        return RedirectResponse(url="/", status_code=303)
    except SQLAlchemyError as e:
        print(f"Database error in delete_item: {str(e)}")
        return templates.TemplateResponse("error.html", {"request": request, "error": "Database error occurred"}, status_code=500)
    except Exception as e:
        print(f"Unexpected error in delete_item: {str(e)}")
        return templates.TemplateResponse("error.html", {"request": request, "error": "An unexpected error occurred"}, status_code=500)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)