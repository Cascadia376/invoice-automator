from fastapi import FastAPI, Request, Depends, Response
from typing import Optional
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
import os
import traceback
import models, database, jobs
from routers import invoices, vendors, gl_categories, debug, issues, admin, auth_router, stellar, reports
import auth
import sys

# --- Environment & Security Configuration ---
ENV = os.getenv("ENV", "development").lower()
IS_PROD = ENV == "production"

# Production Guardrails
if IS_PROD:
    print("🔒 SECURITY: Production Mode Active")
    # Force strict auth in production
    os.environ["AUTH_REQUIRED"] = "true"
    os.environ["DISABLE_AUTH"] = "false"
    
    # Reload auth module to pick up environment changes if needed, 
    # but since we set os.environ before accessing auth properties that usually read strictly from env, 
    # we should check if auth needs re-initialization. 
    # In this specific codebase, auth.py reads env vars at module level.
    # To be safe, we verify compliance:
    if str(os.getenv("DISABLE_AUTH")).lower() == "true":
        print("❌ FATAL: DISABLE_AUTH=true is not allowed in production.")
        sys.exit(1)
        
    auth.AUTH_REQUIRED = True
    auth.DISABLE_AUTH = False

ENABLE_DEBUG_ROUTES = os.getenv("ENABLE_DEBUG_ROUTES", "false").lower() == "true"

models.Base.metadata.create_all(bind=database.engine)

app = FastAPI(
    title="Invoice Automator API",
    description="Backend API for Invoice Automator",
    version="1.2.0",
    docs_url=None if IS_PROD else "/docs",
    redoc_url=None if IS_PROD else "/redoc"
)

# CORS configuration
origins = [
    "http://localhost:8080",
    "http://localhost:5173",
    "http://localhost:3000",
    "https://cascadia-invoice-automator.vercel.app",
    "https://cascadia376-invoice-automator.vercel.app",
    "https://invoice-backend-a1gb.onrender.com", 
]

# Strict CORS for production
allow_origin_regex = "https://.*\.vercel\.app" if not IS_PROD else None

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_origin_regex=allow_origin_regex, 
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "x-organization-id", "x-api-key"],
    expose_headers=[] # No exposing headers by default
)

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["X-Frame-Options"] = "DENY"
        # HSTS (Strict-Transport-Security) only if in production and HTTPS
        if IS_PROD:
             response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        return response

class SizeLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, max_upload_size: int = 10 * 1024 * 1024): # 10MB default
        super().__init__(app)
        self.max_upload_size = max_upload_size
        
    async def dispatch(self, request: Request, call_next):
        if request.method == "POST":
            content_length = request.headers.get("content-length")
            if content_length:
                if int(content_length) > self.max_upload_size:
                    return JSONResponse(status_code=413, content={"detail": "Request entity too large"})
        return await call_next(request)

import time
from collections import defaultdict

class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, requests_per_minute: int = 100):
        super().__init__(app)
        self.requests_per_minute = requests_per_minute
        self.request_counts = defaultdict(list)
        
    async def dispatch(self, request: Request, call_next):
        # Allow health checks to bypass
        if request.url.path == "/api/health":
            return await call_next(request)

        client_ip = request.client.host
        now = time.time()
        
        # Clean up old requests
        self.request_counts[client_ip] = [t for t in self.request_counts[client_ip] if t > now - 60]
        
        if len(self.request_counts[client_ip]) >= self.requests_per_minute:
             return JSONResponse(status_code=429, content={"detail": "Too many requests"})
             
        self.request_counts[client_ip].append(now)
        return await call_next(request)

app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(RateLimitMiddleware)
app.add_middleware(SizeLimitMiddleware)

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    print(f"GLOBAL ERROR: {exc}")
    
    # Only print full traceback in non-prod or if specifically enabled
    if not IS_PROD:
        traceback.print_exc()
        error_trace = traceback.format_exc()
    else:
        # In prod, log it securely server-side but don't send to client
        traceback.print_exc() # Logs to stdout/stderr which usually goes to secure logging
        error_trace = "Traceback hidden in production"

    origin = request.headers.get("origin")
    
    response_content = {
        "detail": "Internal Server Error" if IS_PROD else str(exc),
        "request_id": request.state.request_id if hasattr(request.state, "request_id") else None
    }
    
    if not IS_PROD:
        response_content["type"] = type(exc).__name__
        response_content["traceback"] = error_trace
        
    response = JSONResponse(status_code=500, content=response_content)
    
    if origin and (origin in origins or ".vercel.app" in origin):
        response.headers["Access-Control-Allow-Origin"] = origin
        response.headers["Access-Control-Allow-Credentials"] = "true"
        response.headers["Access-Control-Allow-Methods"] = "*"
        response.headers["Access-Control-Allow-Headers"] = "*"
    return response

# Include Routers
app.include_router(invoices.router)
app.include_router(vendors.router)
app.include_router(gl_categories.router)
app.include_router(issues.router)
app.include_router(admin.router)
app.include_router(stellar.router)

if not IS_PROD and ENABLE_DEBUG_ROUTES:
    print("⚠️ WARNING: Debug routes enabled")
    app.include_router(debug.router)
app.include_router(auth_router.router)
app.include_router(reports.router)

@app.get("/")
@app.get("/api/health")
def health_check():
    return {
        "status": "ok", 
        "version": "1.1.0",
        "database": "postgres",
        "auth_required": auth.AUTH_REQUIRED,
        "supabase_url": bool(auth.SUPABASE_URL),
        "supabase_jwt_secret_present": bool(auth.SUPABASE_JWT_SECRET),
        "jwks_client_ready": bool(auth.jwks_cache.currsize > 0 if hasattr(auth.jwks_cache, "currsize") else "jwks" in auth.jwks_cache)
    }

@app.get("/whoami")
@app.get("/api/whoami")
async def whoami(claims: Optional[dict] = Depends(auth.get_supabase_user)):
    """
    Returns the current authentication status and user information.
    """
    if not claims:
        return {
            "authenticated": False,
            "user_id": None,
            "email": None,
            "auth_required": auth.AUTH_REQUIRED
        }
    
    # Filter safe claims (remove internal JWT noise)
    safe_claims = {
        k: v for k, v in claims.items() 
        if k not in ["nonce", "at_hash", "c_hash", "sid", "amr"]
    }
    
    return {
        "authenticated": True,
        "user_id": claims.get("sub"),
        "email": claims.get("email"),
        "auth_required": auth.AUTH_REQUIRED,
        "claims": safe_claims
    }
