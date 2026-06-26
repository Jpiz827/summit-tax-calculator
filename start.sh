#!/bin/bash
# Railway start script - listen on fixed port 5002
exec gunicorn wsgi:app --bind 0.0.0.0:5002