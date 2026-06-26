#!/bin/bash
# Railway start script - gunicorn on port 5002, Railway proxies to it
exec gunicorn wsgi:app --bind 0.0.0.0:5002