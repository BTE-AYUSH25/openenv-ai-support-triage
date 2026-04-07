# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.

import time
import os
import psutil
import argparse
import uvicorn
import gradio as gr
from uuid import uuid4
from typing import Dict, Any, Type, Optional
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse, HTMLResponse

from openenv_core.env_server.http_server import create_app
from .ai_support_triage_environment import AiSupportTriageEnvironment
from ai_support_triage.models import SupportAction, SupportObservation, Category, Priority, EscalationTarget, TicketStatus

# --- Metrics (Rule 16) ---
METRICS = {
    "total_executions": 0,
    "error_rate": 0.0,
    "avg_execution_time_ms": 0.0,
    "memory_usage_mb": 0.0,
}

START_TIME = time.time()

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
    try:
        response = await call_next(request)
    except Exception as e:
        # Fallback response for unhandled exceptions in middleware context
        METRICS["error_rate"] = (METRICS["error_rate"] * 0.9) + 0.1
        return JSONResponse(status_code=500, content={"success": False, "error": str(e)})
        
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

# --- Rule 23: Structured task Selection ---
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

# --- Legendary HUD Dashboard (Rule 16 Visuals) ---
@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard():
    """Power Option: Human-readable observability HUD."""
    metrics_data = await get_metrics()
    m = metrics_data["metrics"]
    s = metrics_data["system"]
    
    html = f"""
    <html>
        <head>
            <title>AI Support Operations HUD</title>
            <style>
                body {{ font-family: 'Outfit', sans-serif; background: #0b0e14; color: #e1e1e1; margin: 0; display: flex; justify-content: center; align-items: center; height: 100vh; }}
                .card {{ background: #1a1f26; border: 1px solid #2d333b; border-radius: 12px; padding: 30px; box-shadow: 0 10px 30px rgba(0,0,0,0.5); width: 450px; }}
                h1 {{ color: #4facfe; margin-top: 0; font-size: 1.5em; border-bottom: 2px solid #4facfe; padding-bottom: 10px; }}
                .metric {{ display: flex; justify-content: space-between; padding: 12px 0; border-bottom: 1px solid #2d333b; }}
                .label {{ color: #888; font-weight: 500; }}
                .value {{ color: #00f2fe; font-weight: 700; font-family: 'Courier New', monospace; }}
                .status {{ color: #00ff00; font-weight: bold; }}
                .footer {{ font-size: 0.75em; color: #555; margin-top: 25px; text-align: center; font-style: italic; }}
            </style>
            <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@400;700&display=swap" rel="stylesheet">
        </head>
        <body>
            <div class="card">
                <h1>🚀 OPS MISSION CONTROL</h1>
                <div class="metric"><span class="label">System Engine</span><span class="status">ACTIVE</span></div>
                <div class="metric"><span class="label">Avg Latency</span><span class="value">{m['avg_execution_time_ms']:.2f} ms</span></div>
                <div class="metric"><span class="label">Memory Usage</span><span class="value">{m['memory_usage_mb']} MB</span></div>
                <div class="metric"><span class="label">Error Rate</span><span class="value">{m['error_rate']:.2%}</span></div>
                <div class="metric"><span class="label">Uptime</span><span class="value">{s['uptime_seconds']:.0f}s</span></div>
                <div class="footer">Rule 16 Compliant • Project: {s['environment']} v{s['version']}</div>
            </div>
        </body>
    </html>
    """
    return html

# --- Gradio UI Battle Station ---
def create_ui():
    with gr.Blocks(title="AI Support Triage Explorer", css=".gradio-container {background-color: #0b0e14}") as demo:
        gr.Markdown("# 🔍 AI Support Triage - Legendary Explorer")
        
        with gr.Row():
            with gr.Column(scale=2):
                with gr.Group():
                    gr.Markdown("### 🛠️ Agent Action Interface")
                    action_draft = gr.Textbox(label="Response Draft", placeholder="Type response as an AI agent...", lines=3)
                    with gr.Row():
                        action_cat = gr.Dropdown(label="Category", choices=[e.value for e in Category])
                        action_prio = gr.Dropdown(label="Priority", choices=[e.value for e in Priority])
                    with gr.Row():
                        action_esc = gr.Dropdown(label="Escalation", choices=[e.value for e in EscalationTarget])
                        action_stat = gr.Dropdown(label="New Status", choices=[e.value for e in TicketStatus])
                    
                    with gr.Row():
                        step_btn = gr.Button("🚀 Execute Action (step)", variant="primary")
                        reset_btn = gr.Button("♻️ Reset / Next Task", variant="secondary")
            
            with gr.Column(scale=1):
                gr.Markdown("### 📊 Live State & Reward")
                obs_display = gr.JSON(label="Observation")
                rew_display = gr.Number(label="Last Step Reward", precision=3)
                done_display = gr.Checkbox(label="Episode Done")
                
                gr.Markdown("---")
                gr.Markdown("### 📈 Live Metrics Dashboard")
                metrics_html = gr.HTML()

        def update_metrics():
            process = psutil.Process(os.getpid())
            mem = round(process.memory_info().rss / (1024 * 1024), 2)
            uptime = time.time() - START_TIME
            
            return f"""
            <div style='background:#1a1f26; padding:15px; border-radius:8px; border:1px solid #2d333b;'>
                <div style='display:flex; justify-content:space-between; margin-bottom:5px;'>
                    <span style='color:#888;'>Latency:</span><span style='color:#00f2fe;font-weight:bold;'>{METRICS['avg_execution_time_ms']:.2f}ms</span>
                </div>
                <div style='display:flex; justify-content:space-between; margin-bottom:5px;'>
                    <span style='color:#888;'>Memory:</span><span style='color:#00f2fe;font-weight:bold;'>{mem}MB</span>
                </div>
                <div style='display:flex; justify-content:space-between;'>
                    <span style='color:#888;'>Uptime:</span><span style='color:#00f2fe;font-weight:bold;'>{uptime:.0f}s</span>
                </div>
            </div>
            """

        def ui_reset():
            observation = env.reset()
            return observation, 0, False, update_metrics()

        def ui_step(draft, cat, prio, esc, stat):
            try:
                action = SupportAction(
                    response_draft=draft,
                    assigned_category=cat,
                    assigned_priority=prio,
                    escalated_to=esc,
                    new_status=stat
                )
                obs, reward, done, _ = env.step(action)
                return obs, reward, done, update_metrics()
            except Exception as e:
                return {"error": str(e)}, 0, False, update_metrics()

        reset_btn.click(ui_reset, outputs=[obs_display, rew_display, done_display, metrics_html])
        step_btn.click(ui_step, inputs=[action_draft, action_cat, action_prio, action_esc, action_stat], 
                      outputs=[obs_display, rew_display, done_display, metrics_html])
        
        demo.load(ui_reset, outputs=[obs_display, rew_display, done_display, metrics_html])

    return demo

# Mount the Legendary Gradio UI at /web
app = gr.mount_gradio_app(app, create_ui(), path="/web")

# --- Rule 8: Structured Error Handler ---
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

def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=7860)
    args = parser.parse_args()
    uvicorn.run(app, host="0.0.0.0", port=args.port)

if __name__ == "__main__":
    main()
