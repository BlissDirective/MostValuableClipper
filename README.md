# MVC - Monetized Video Content

A complete system for turning long-form video content into monetized short-form clips across multiple platforms.

## Project Structure

```
mvc-combined/
├── backend/              # FastAPI backend
│   ├── app/
│   │   ├── api/          # API route handlers
│   │   ├── core/         # Config, logging, events
│   │   ├── services/     # Business logic
│   │   ├── models.py     # Pydantic models
│   │   └── main.py       # Application entry
│   ├── scripts/          # Utility scripts
│   ├── tests/            # Test suite
│   ├── Dockerfile        # Container image
│   ├── fly.toml          # Fly.io deployment config
│   ├── deploy.sh         # Deployment script
│   └── requirements.txt  # Python dependencies
├── frontend/             # React Native (future)
├── docker-compose.yml    # Local dev stack
├── Makefile             # Common commands
└── env.var              # Environment template

```

## Quick Start

### Prerequisites

- Python 3.11+
- Docker (optional, for local dev)
- Fly.io CLI (`flyctl`)

### 1. Install Backend Dependencies

```bash
cd backend
pip install -r requirements.txt
```

### 2. Configure Environment

```bash
cp env.var .env
# Edit .env with your actual API keys
```

### 3. Run Locally

```bash
make dev
# Or directly:
cd backend && uvicorn app.main:app --reload --port 8000
```

### 4. Run Tests

```bash
make test
```

### 5. Deploy to Fly.io

```bash
make fly-deploy
# Or directly:
cd backend && ./deploy.sh
```

## Architecture

### Backend Services

| Service | Technology | Purpose |
|---------|-----------|---------|
| API Server | FastAPI | HTTP API |
| Database | Supabase (PostgreSQL) | Data persistence |
| Cache/Queue | Upstash Redis | Job queue, caching |
| Storage | Cloudflare R2 | Video clip storage |
| Payments | Stripe | Subscriptions |
| AI Pipeline | LangGraph | Clip generation workflow |

### API Endpoints

- `GET /api/v1/health` - Health check
- `GET /api/v1/users/me` - Current user
- `GET /api/v1/clips` - List clips
- `POST /api/v1/clips` - Create clip
- `GET /api/v1/pipelines` - List pipelines
- `POST /api/v1/pipelines` - Create pipeline
- `GET /api/v1/sources` - List video sources
- `POST /api/v1/sources` - Add source
- `GET /api/v1/earnings` - Revenue data
- `POST /api/v1/webhooks/stripe` - Stripe webhooks

## Development

### Docker Compose (Recommended)

```bash
docker-compose up --build
```

This starts:
- API server on port 8000
- Redis on port 6379

### Seeding Data

```bash
make seed
```

## Environment Variables

All required variables are documented in `env.var`. Key ones:

- `SUPABASE_URL` / `SUPABASE_SERVICE_ROLE_KEY` - Database
- `UPSTASH_REDIS_REST_URL` / `UPSTASH_REDIS_REST_TOKEN` - Queue/Cache
- `CLOUDFLARE_R2_*` - Object storage
- `STRIPE_SECRET_KEY` / `STRIPE_WEBHOOK_SECRET` - Payments
- `FLY_API_TOKEN` - Deployment

## License

MIT
