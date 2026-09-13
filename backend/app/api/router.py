from fastapi import APIRouter

from app.api.routes import assistant, ats, auth, documents, interviews, performance, system

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(documents.router)
api_router.include_router(ats.router)
api_router.include_router(interviews.router)
api_router.include_router(performance.router)
api_router.include_router(assistant.router)
api_router.include_router(system.router)
