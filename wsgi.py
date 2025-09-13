#!/usr/bin/env python3
"""
WSGI entry point for Vercel deployment
"""

from app import app

# This is the entry point that Vercel will use
if __name__ == "__main__":
    app.run()
