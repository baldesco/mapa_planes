from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings, logger
from app.routers import api_auth, api_places, forms, pages, system

# --- App Initialization ---
app = FastAPI(
    title="Mapa Planes",
    description="A web app to manage and map places to visit.",
    version="1.0.0",
    # Optional: Add docs_url=None, redoc_url=None in production if API docs are not public
    # docs_url="/api/docs" if settings.APP_ENV == "development" else None,
    # redoc_url="/api/redoc" if settings.APP_ENV == "development" else None,
)

# --- CORS Middleware ---
if settings.BACKEND_CORS_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[str(origin).strip() for origin in settings.BACKEND_CORS_ORIGINS],
        allow_credentials=True,  # Important for cookies
        allow_methods=["*"],
        allow_headers=["*"],
    )
    logger.info(f"CORS enabled for origins: {settings.BACKEND_CORS_ORIGINS}")
else:
    logger.warning("CORS is not configured. BACKEND_CORS_ORIGINS is empty.")


# --- Static Files ---
# Serve static files (CSS, JS) from the 'static' directory
app.mount("/static", StaticFiles(directory="static"), name="static")
logger.info("Static files mounted from './static' directory at '/static'.")


# --- Include Routers ---
# API Routers (prefixed with /api/v1)
app.include_router(api_auth.router)
app.include_router(api_places.router)
app.include_router(system.router)  # Includes /health and /api/v1/geocode

# Page Serving and Form Handling Routers (no prefix)
app.include_router(pages.router)
app.include_router(forms.router)

logger.info("All application routers included.")

# --- Root endpoint (optional, can be removed if pages.router handles '/') ---
# @app.get("/")
# async def read_root_redirect():
#     # Redirect to the main page served by pages.router
#     from fastapi.responses import RedirectResponse
#     return RedirectResponse(url="/app") # Assuming pages router handles /app

# Add any application startup/shutdown events here if needed
# @app.on_event("startup")
# async def startup_event():
#     logger.info("Application startup...")
#
# @app.on_event("shutdown")
# async def shutdown_event():
#     logger.info("Application shutdown.")
