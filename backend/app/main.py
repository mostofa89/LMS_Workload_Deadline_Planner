from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.controllers.exceptions import AppError
from app.views import identity_router

app = FastAPI(title="LMS Workload Deadline Planner")

# Include Authentication & Identity Router
app.include_router(identity_router, prefix="/api/v1")
app.include_router(identity_router)


@app.exception_handler(AppError)
async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content=exc.to_dict(),
    )


@app.get("/")
def root() -> dict[str, str]:
    return {"message": "LMS Workload Deadline Planner API", "health": "/api/health"}


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
