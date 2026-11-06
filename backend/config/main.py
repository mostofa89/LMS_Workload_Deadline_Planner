from fastapi import FastAPI

app = FastAPI(title="LMS Workload Deadline Planner")


@app.get("/")
def root() -> dict[str, str]:
    return {"message": "LMS Workload Deadline Planner API", "health": "/api/health"}


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
