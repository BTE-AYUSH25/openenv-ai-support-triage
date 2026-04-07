# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.

import time
import os
import psutil
from uuid import uuid4
from typing import Dict, Any, Type, Optional

from openenv_core.env_server.http_server import create_app
from .ai_support_triage_environment import AiSupportTriageEnvironment
from ai_support_triage.models import SupportAction, SupportObservation

# --- Metrics (Rule 16) ---
METRICS = {
    "total_executions": 0,
    "error_rate": 0.0,
    "avg_execution_time_ms": 0.0,
    "memory_usage_mb": 0.0,
}

# --- Create Environment ---
env = AiSupportTriageEnvironment()

# --- Create FastAPI App ---
app = create_app(
    env,
    SupportAction,
    SupportObservation,
    env_name="ai_support_triage",
)

# --- Add Middleware for Rule 16 (Correlation ID and Timing) ---
@app.middleware("http")
async def add_process_time_header(request, call_next):
    correlation_id = request.headers.get("X-Correlation-ID", str(uuid4()))
    start_time = time.time()
    
    # Process request
    response = await call_next(request)
    
    # Update metrics
    process_time = (time.time() - start_time) * 1000
    METRICS["total_executions"] += 1
    # Rolling average
    METRICS["avg_execution_time_ms"] = (
        (METRICS["avg_execution_time_ms"] * (METRICS["total_executions"] - 1) + process_time)
        / METRICS["total_executions"]
    )
    
    response.headers["X-Correlation-ID"] = correlation_id
    response.headers["X-Process-Time-MS"] = str(round(process_time, 2))
    return response

from pydantic import BaseModel

class SelectTaskRequest(BaseModel):
    task_id: str

@app.post("/select_task")
async def select_task(request: SelectTaskRequest):
    """Rule 23: Structured task Selection."""
    try:
        env.select_task(request.task_id)
        return {"success": True, "task_id": request.task_id}
    except Exception as e:
        return JSONResponse(status_code=400, content={"success": False, "error": str(e)})

import time
START_TIME = time.time()

# --- Rule 16: Metrics Endpoint ---
@app.get("/metrics")
async def get_metrics() -> Dict[str, Any]:
    """Expose metrics according to SST Hackathon standards."""
    process = psutil.Process(os.getpid())
    METRICS["memory_usage_mb"] = round(process.memory_info().rss / (1024 * 1024), 2)
    uptime = time.time() - START_TIME
    return {
        "success": True,
        "metrics": METRICS,
        "system": {
            "environment": "ai_support_triage",
            "uptime_seconds": round(uptime, 2),
            "version": "1.0.0"
        }
    }

# --- Rule 8: Structured Error Handler ---
from fastapi import Request
from fastapi.responses import JSONResponse

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    METRICS["error_rate"] = (METRICS["error_rate"] * 0.9) + 0.1 # Simple decay
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "error": {
                "type": type(exc).__name__,
                "message": str(exc),
                "context": f"Request to {request.url.path} failed."
            }
        },
    )

def main(host: str = "0.0.0.0", port: int = 7860):
    import uvicorn
    uvicorn.run(app, host=host, port=port)

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=7860)
    args = parser.parse_args()
    main(port=args.port)
