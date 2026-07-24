"""
scripts/seed_dev_data.py

WHY THIS FILE EXISTS
---------------------
Every backend project eventually needs a repeatable way to populate a fresh
database with sample data for local development, without going through the
(not-yet-built) signup UI by hand every time.

This is a thin, runnable script — not a test, not application code — which
is exactly why it lives in `scripts/` rather than `tests/` or `services/`.

Run with: `python -m scripts.seed_dev_data` from the backend/ root.
"""

from __future__ import annotations

from database.session import SessionLocal
from schemas.user import UserCreate
from services.user_service import UserService


def run() -> None:
    db = SessionLocal()
    try:
        service = UserService(db)
        user = service.register_user(
            UserCreate(email="demo@example.com", password="devpassword123", full_name="Demo User")
        )
        print(f"Seeded demo user: {user.email} ({user.id})")
    finally:
        db.close()


if __name__ == "__main__":
    run()
    