from fastapi import FastAPI, Request, HTTPException, status
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware


from app.core.config import settings, logger
from app.routers import api_auth, api_places, forms, pages, system
from app.routers import api_visits
from app.middleware import AuthRedirectMiddleware

# --- App Initialization ---
app = FastAPI(
    title="Mapa Planes",
    description="A web app to manage and map places to visit.",
    version="1.0.0",  # Consider updating version as features are added, e.g., 1.1.0
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

# --- Add Supabase Async Client to App State (Optional but useful for middleware) ---
# This requires installing supabase[async] -> pip install supabase[async] httpx[http2]
# If you don't want the async dependency, the middleware needs to use asyncio.to_thread
# for the db_client.auth.get_user call.
# from supabase_async import create_client as create_async_client, AsyncClient
# @app.on_event("startup")
# async def startup_event():
#     logger.info("Application startup...")
#     if settings.SUPABASE_URL and settings.SUPABASE_KEY:
#         try:
#             # Note: Using anon key for the state client, as it's mainly for get_user checks
#             app.state.supabase_async_client = create_async_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)
#             logger.info("Supabase async client initialized and added to app state.")
#         except Exception as e:
#             logger.error(f"Failed to initialize Supabase async client: {e}", exc_info=True)
#             app.state.supabase_async_client = None
#     else:
#         app.state.supabase_async_client = None
#
# @app.on_event("shutdown")
# async def shutdown_event():
#     logger.info("Application shutdown.")
#     if hasattr(app.state, 'supabase_async_client') and app.state.supabase_async_client:
#         try:
#             await app.state.supabase_async_client.aclose()
#             logger.info("Supabase async client closed.")
#         except Exception as e:
#             logger.error(f"Error closing Supabase async client: {e}", exc_info=True)
