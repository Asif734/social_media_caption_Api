

from fastapi import FastAPI
from app.api.v1.api import api_router

app = FastAPI(title="Caption Generator")

@api_router.get("/")
def api_root():
    return {"message": "API v1 working"}
# Register API routes
app.include_router(api_router, prefix="/api/v1")