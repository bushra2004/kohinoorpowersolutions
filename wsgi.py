# wsgi.py - Entry point for Vercel
from app import app

# This is needed for Vercel serverless deployment
handler = app