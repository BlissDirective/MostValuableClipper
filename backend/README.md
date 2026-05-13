# Setup Script for MVC Backend

## Prerequisites

- Python 3.11+
- Docker (for local development)
- Fly.io CLI (`flyctl`)

## Quick Start

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Set up environment variables:**
   ```bash
   cp env.var .env
   # Edit .env with your actual API keys
   ```

3. **Run locally:**
   ```bash
   uvicorn app.main:app --reload --port 8000
   ```

4. **Deploy to Fly.io:**
   ```bash
   ./deploy.sh
   ```

## API Documentation

When running locally, visit:
- Swagger UI: http://localhost:8000/api/docs
- ReDoc: http://localhost:8000/api/redoc

## Architecture

```
app/
├── api/           # FastAPI route handlers
├── core/          # Config, logging, events
├── models.py      # Pydantic models
├── services/      # Business logic
│   ├── auth.py         # JWT auth
│   ├── database.py     # Supabase operations
│   ├── stripe_service.py  # Payments
│   ├── r2_service.py    # Cloudflare storage
│   ├── queue.py         # Redis jobs
│   └── langgraph_service.py  # AI pipeline
└── main.py        # Application entry
```
