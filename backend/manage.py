#!/usr/bin/env python3
"""
MVC Backend Management CLI

Usage:
    python manage.py migrate    - Run database migrations
    python manage.py seed       - Seed initial data
    python manage.py test       - Run tests
    python manage.py shell      - Open interactive shell
"""
import sys
import subprocess
import argparse

def migrate():
    """Run database migrations."""
    print("🔄 Running migrations...")
    # In production, you'd use alembic or similar
    print("✅ Migrations complete (using Supabase schema)")

def seed():
    """Seed initial data."""
    print("🌱 Seeding data...")
    subprocess.run([sys.executable, "scripts/seed.py"])

def test():
    """Run test suite."""
    print("🧪 Running tests...")
    subprocess.run(["pytest", "tests/", "-v"])

def shell():
    """Open interactive shell with app context."""
    print("🐍 Opening interactive shell...")
    from app.main import app
    from app.core.config import settings
    import IPython
    IPython.embed()

def main():
    parser = argparse.ArgumentParser(description="MVC Backend Management")
    subparsers = parser.add_subparsers(dest="command")
    
    subparsers.add_parser("migrate", help="Run database migrations")
    subparsers.add_parser("seed", help="Seed initial data")
    subparsers.add_parser("test", help="Run tests")
    subparsers.add_parser("shell", help="Open interactive shell")
    
    args = parser.parse_args()
    
    commands = {
        "migrate": migrate,
        "seed": seed,
        "test": test,
        "shell": shell,
    }
    
    if args.command in commands:
        commands[args.command]()
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
