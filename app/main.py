from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings, logger
from app.routers import api_auth, api_places, forms, pages, system, api_visits
from app.middleware import AuthRedirectMiddleware

# --- App Initialization ---
app = FastAPI(
    title="Mapa Planes",
    description="A web app to manage and map places to visit.",
    version="1.1.0", # Incremented for SPA-lite and Sidebar features
)

# --- Add Middleware ---
# AuthRedirectMiddleware must come before routers to protect page routes
app.add_middleware(AuthRedirectMiddleware)

if settings.BACKEND_CORS_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[str(origin).strip() for origin in settings.BACKEND_CORS_ORIGINS],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    logger.info(f"CORS enabled for origins: {settings.BACKEND_CORS_ORIGINS}")

# --- Static Files ---
# Mounted before routers to ensure assets are available for all pages
app.mount("/static", StaticFiles(directory="static"), name="static")

# --- Include Routers ---
# API routes prioritized for the SPA-lite frontend
app.include_router(api_auth.router)
app.include_router(api_places.router)
app.include_router(api_visits.router)
app.include_router(system.router)

# Page and Form routes (Forms handled by JS, but kept as fallbacks)
app.include_router(pages.router)
app.include_router(forms.router)

logger.info("Application routers and middleware fully initialized.")