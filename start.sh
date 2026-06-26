#!/bin/bash
# Railway start script - properly expands PORT env variable
exec gunicorn wsgi:app --bind 0.0.0.0:${PORT:-5002}