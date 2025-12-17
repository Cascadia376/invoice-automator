from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import os
import models, database
from routers import invoices, vendors, gl_categories, debug

models.Base.metadata.create_all(bind=database.engine)

app = FastAPI()

# CORS configuration
origins = [
    "http://localhost:8080",
    "http://localhost:5173",
    "https://cascadia-invoice-automator.vercel.app",
    "https://cascadia376-invoice-automator.vercel.app",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_origin_regex="https://invoice-automator-.*-cascadia376\.vercel\.app", # Support preview deployments
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"]
)

# Use absolute path for uploads to avoid CWD issues
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")

# Include Routers
app.include_router(invoices.router)
app.include_router(vendors.router)
app.include_router(gl_categories.router)
app.include_router(debug.router)

@app.get("/")
def health_check():
    from database import SQLALCHEMY_DATABASE_URL
    db_type = "postgres" if "postgres" in SQLALCHEMY_DATABASE_URL else "sqlite"
    return {
        "status": "ok", 
        "version": "1.0.0",
        "database": db_type,
        "database_url_masked": SQLALCHEMY_DATABASE_URL.split("@")[-1] if "@" in SQLALCHEMY_DATABASE_URL else "sqlite_local"
    }
