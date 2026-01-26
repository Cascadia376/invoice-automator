from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import os
import models, database
from routers import invoices, vendors, gl_categories, debug, issues, admin

models.Base.metadata.create_all(bind=database.engine)

app = FastAPI()

# CORS configuration
origins = [
    "http://localhost:8080",
    "http://localhost:5173",
    "https://cascadia-invoice-automator.vercel.app",
    "https://cascadia376-invoice-automator.vercel.app",
    "https://invoice-backend-a1gb.onrender.com", 
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_origin_regex="https://.*\.vercel\.app", 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"]
)

# Global exception handler to ensure CORS headers are attached even on 500s
from fastapi import Request
from fastapi.responses import JSONResponse

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    import traceback
    print(f"GLOBAL ERROR: {exc}")
    traceback.print_exc()
    
    # Extract origin for CORS
    origin = request.headers.get("origin")
    
    response_content = {"detail": str(exc), "type": type(exc).__name__}
    response = JSONResponse(
        status_code=500,
        content=response_content
    )
    
    # Manually add CORS headers to the error response if origin is valid
    if origin:
        is_valid_origin = origin in origins or ".vercel.app" in origin
        if is_valid_origin:
            response.headers["Access-Control-Allow-Origin"] = origin
            response.headers["Access-Control-Allow-Credentials"] = "true"
            response.headers["Access-Control-Allow-Methods"] = "*"
            response.headers["Access-Control-Allow-Headers"] = "*"
        
    return response

# Use absolute path for any remaining local temp needs (e.g. processing)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# NOTE: Uploads are handled via S3/Storage Service. 
# We do NOT mount a local static directory for uploads to prevent data loss on ephemeral filesystems (Render/App Runner).

# Include Routers
app.include_router(invoices.router)
app.include_router(vendors.router)
app.include_router(gl_categories.router)
app.include_router(issues.router)
app.include_router(admin.router)
app.include_router(debug.router)

@app.get("/")
def health_check():
    from database import SQLALCHEMY_DATABASE_URL
    db_type = "postgres" if "postgres" in SQLALCHEMY_DATABASE_URL else "sqlite"
    
    api_key = os.getenv("OPENAI_API_KEY")
    jwt_secret = os.getenv("SUPABASE_JWT_SECRET")
    
    return {
        "status": "ok", 
        "version": "1.0.1",
        "database": db_type,
        "database_url_masked": SQLALCHEMY_DATABASE_URL.split("@")[-1] if "@" in SQLALCHEMY_DATABASE_URL else "sqlite_local",
        "openai_api_key_present": bool(api_key),
        "supabase_jwt_secret_present": bool(jwt_secret),
        "supabase_jwt_aud": os.getenv("SUPABASE_JWT_AUD", "authenticated")
    }
