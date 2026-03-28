"""Vercel serverless function entry point.

Imports the FastAPI app from backend/main.py so Vercel can serve it
as a Python function.  Static files are served by Vercel's CDN; the
SafeStaticFiles mount is skipped when the VERCEL env var is set.
"""

from backend.main import app  # noqa: F401 — Vercel detects the ASGI app
