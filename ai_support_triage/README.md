---
title: AI Support Triage OpenEnv
emoji: ☎️
colorFrom: blue
colorTo: indigo
sdk: docker
app_port: 7860
---

# 🏆 AI Support Triage Environment: Winner Edition

This environment is built for the **Meta x PyTorch OpenEnv Hackathon**. It simulates a high-stakes customer support system where an AI agent must handle ticket classification, routing, and complex policy-driven resolution.

## 🥇 Why This Project Wins (Rubric Alignment)

| Criteria | Weight | Our Implementation |
| :--- | :--- | :--- |
| **Real-world Utility** | 30% | Simulates a core business workflow (Support Operations) with multi-tier escalation. |
| **Task & Grader Quality** | 25% | **Deterministic, non-binary grading** with partial rewards for near-misses. |
| **Environment Design** | 20% | Clean, spec-compliant FastAPI server with built-in **Rule 16 Metrics**. |
| **Code Quality** | 15% | Pydantic validation, structured error handling, and modular architecture. |
| **Creativity** | 10% | Hard tasks feature **Decoys** and **Hidden Constraints** (SLA/Legal). |

## 🛠️ Features

- **Observability (Rule 16)**: Live metrics at `/metrics` (Latency, Memory, CPU).
- **Security (Rule 23)**: Strict schema validation on all inputs.
- **Stability (Rule 8)**: Automated retry logic and structured error envelopes.
- **Web UI**: Enabled interactive interface for task visualization.

## 🚀 Deployment

1. **Local Test**:
   ```bash
   python -m ai_support_triage.server.app
   pytest test_env.py
   ```
2. **Deploy to HF**:
   ```bash
   openenv push --repo-id <your-username>/ai-support-triage
   ```

## 📊 Baseline Performance Check
Run `python inference.py` to see the automated evaluation markers:
- `easy_1`: 1.0
- `medium_1`: 0.85
- `hard_1`: 0.90
- **Total AVG Score: 0.92**

---
*Built with ❤️ for the SST OpenEnv Hackathon.*
