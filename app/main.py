from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, HTTPException, status
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware


from app.core.config import settings, logger
from app.routers import api_auth, api_places, forms, pages, system
from app.routers import api_visits
from app.middleware import AuthRedirectMiddleware
from app.db.setup import init_service_client

# --- Lifespan Events ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Initialize shared service client
    logger.info("Application starting up...")
    await init_service_client()
    yield
    # Shutdown: Cleanup if needed
    logger.info("Application shutting down...")

# --- App Initialization ---
app = FastAPI(
    title="Mapa Planes",
    description="A web app to manage and map places to visit.",
    version="1.0.0",
    lifespan=lifespan
)

# --- Add Middleware ---
if settings.BACKEND_CORS_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[str(origin).strip() for origin in settings.BACKEND_CORS_ORIGINS],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    logger.info(f"CORS enabled for origins: {settings.BACKEND_CORS_ORIGINS}")
else:
    logger.warning("CORS is not configured. BACKEND_CORS_ORIGINS is empty.")

app.add_middleware(AuthRedirectMiddleware)
logger.info("AuthRedirectMiddleware added.")


# --- Static Files ---
app.mount("/static", StaticFiles(directory="static"), name="static")
logger.info("Static files mounted from './static' directory at '/static'.")


# --- Include Routers ---
app.include_router(api_auth.router)
app.include_router(api_places.router)
app.include_router(api_visits.router)
app.include_router(system.router)
app.include_router(pages.router)
app.include_router(forms.router)

logger.info("All application routers included.")
