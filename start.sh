#!/bin/bash
# Railway start script - bind to Railway's assigned $PORT (fallback 5002 for local runs)
exec gunicorn wsgi:app --bind 0.0.0.0:${PORT:-5002}