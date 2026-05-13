.PHONY: install dev test lint format seed deploy fly-deploy

install:
	cd backend && pip install -r requirements.txt

dev:
	cd backend && uvicorn app.main:app --reload --port 8000

test:
	cd backend && pytest tests/ -v

lint:
	cd backend && flake8 app/ --max-line-length=120

format:
	cd backend && black app/ --line-length=120

seed:
	cd backend && python scripts/seed.py

docker-up:
	docker-compose up --build

docker-down:
	docker-compose down

fly-deploy:
	cd backend && ./deploy.sh

fly-logs:
	fly logs -a mvc-backend

fly-status:
	fly status -a mvc-backend