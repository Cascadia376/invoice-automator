from fastapi import FastAPI, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import os
import traceback
import models, database
from routers import invoices, vendors, gl_categories, debug, issues, admin, auth_router

models.Base.metadata.create_all(bind=database.engine)

app = FastAPI()

# CORS configuration
origins = [
    "http://localhost:8080",
    "http://localhost:5173",
    "http://localhost:3000",
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

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    print(f"GLOBAL ERROR: {exc}")
    traceback.print_exc()
    origin = request.headers.get("origin")
    response_content = {"detail": str(exc), "type": type(exc).__name__}
    response = JSONResponse(status_code=500, content=response_content)
    
    if origin and (origin in origins or ".vercel.app" in origin):
        response.headers["Access-Control-Allow-Origin"] = origin
        response.headers["Access-Control-Allow-Credentials"] = "true"
        response.headers["Access-Control-Allow-Methods"] = "*"
        response.headers["Access-Control-Allow-Headers"] = "*"
    return response

# Use absolute path for any remaining local temp needs
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Include Routers
app.include_router(invoices.router)
app.include_router(vendors.router)
app.include_router(gl_categories.router)
app.include_router(issues.router)
app.include_router(admin.router)
app.include_router(debug.router)
app.include_router(auth_router.router)

@app.get("/")
@app.get("/health")
@app.get("/api/health")
def health_check():
    from database import SQLALCHEMY_DATABASE_URL
    import auth
    db_type = "postgres" if "postgres" in SQLALCHEMY_DATABASE_URL else "sqlite"
    
    return {
        "status": "ok", 
        "version": "1.1.0",
        "database": db_type,
        "auth_required": auth.AUTH_REQUIRED,
        "supabase_url": bool(auth.SUPABASE_URL),
        "supabase_jwt_secret_present": bool(auth.SUPABASE_JWT_SECRET),
        "jwks_client_ready": bool(auth.jwks_client)
    }

@app.get("/whoami")
@app.get("/api/whoami")
async def whoami(ctx: auth.UserContext = Depends(auth.get_current_user)):
    import auth
    return {
        "user_id": ctx.user_id if ctx else None,
        "email": ctx.email if ctx else None,
        "authenticated": ctx is not None,
        "auth_required": auth.AUTH_REQUIRED
    }
