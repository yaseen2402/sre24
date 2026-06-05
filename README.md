# SRE24: The Autonomous Site Reliability Engineer

**An autonomous AI agent that turns 3 AM production incidents into one-click GitHub Pull Requests.**

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)

## Overview

Everyone is "vibe coding" right now, spinning up complex apps in minutes. But when those apps hit production and scale, the AI isn't there to wake up at 3 AM to fix memory leaks or database bottlenecks. 

**SRE24** is a proactive, autonomous agent built with the **Google Agentic Development Kit (ADK)** and **Gemini 2.5 Flash**. 

When a production environment degrades, Dynatrace fires an alert to SRE24. The agent doesn't just read a log - it uses the **Model Context Protocol (MCP)** to actively query live distributed traces via DQL. It then acts as a complete DevOps team:
1. **Ops Hand:** Autonomously scales up Google Cloud Run infrastructure to keep the app alive.
2. **Dev Hand:** Analyzes the trace, fetches the broken source code from GitHub, applies an optimized patch, and creates a ready-to-merge Pull Request.

## Architecture & Tech Stack

- **Agent Core:** Google Agentic Development Kit (ADK) + Gemini 2.5 Flash
- **Telemetry & MCP:** Dynatrace + `@dynatrace-oss/dynatrace-mcp-server`
- **Backend Webhook Server:** FastAPI (Python), SQLAlchemy (Multi-tenant config)
- **Frontend Dashboard:** React, Vite (Deployed on Vercel)
- **Infrastructure Targets:** Google Cloud Run, GitHub API

---

## Getting Started

### 1. Backend Setup (FastAPI & Agent)

Ensure you have Python 3.10+ and Node.js installed (Node is required for the Dynatrace MCP server).

```bash
# Clone the repository
git clone https://github.com/yourusername/sre24.git
cd sre24

# Create a virtual environment and install dependencies
python -m venv venv
source venv/bin/activate  # Or `venv\Scripts\activate` on Windows
pip install -r requirements.txt

# Start the webhook server
python main.py
```
*The backend will run on `http://localhost:8000`.*

### 2. Frontend Setup (React Dashboard)

```bash
# Open a new terminal and navigate to the frontend folder
cd frontend

# Install dependencies and start the dev server
npm install
npm run dev
```
*The frontend dashboard will run on `http://localhost:5173`.*

---

## Configuration & Integration

SRE24 is built to be strictly multi-tenant. You configure your keys directly via the UI dashboard, not hardcoded files.

1. **Open the Dashboard:** Go to your running frontend app.
2. **Link Credentials:** Navigate to the **Config** section and securely input your:
   - Dynatrace URL & Platform Token
   - GitHub Personal Access Token & Target Repository
   - GCP Project ID & Region
3. **Dynatrace Webhook Integration:** Copy your unique SRE24 Webhook URL (e.g., `https://sre24-backend.com/webhook/your-tenant-id`). Go to **Dynatrace -> Integration -> Problem Notifications -> Custom Webhook**, and paste the URL.

That's it! Your autonomous engineer is now officially on-call.

---

## Deployment

The backend is fully dockerized and ready to be deployed to **Google Cloud Run**.

```bash
gcloud run deploy sre24-backend \
  --source . \
  --region us-central1 \
  --allow-unauthenticated \
  --port 8080 \
  --env-vars-file=env.yaml
```

The frontend can be instantly deployed using Vercel or any standard static hosting provider.

## License
This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
