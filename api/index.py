"""
api/index.py — Vercel Serverless Function entry point.
Exposes the FastAPI ASGI application to Vercel's Python runtime.

Vercel automatically detects this file and routes all requests through it
when configured with the rewrites in vercel.json.
"""

import os
import sys

# Ensure the project root is on the Python path so imports like
# `from app.main import app` resolve correctly in Vercel's build environment.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.main import app  # noqa: E402 — path manipulation above

# Vercel expects an ASGI-compatible `app` object at module level.
# FastAPI is ASGI-native, so no wrapper is needed.
