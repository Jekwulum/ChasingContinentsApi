#!/bin/bash
echo "Starting the application"
python -m pip install --upgrade pip
pip install -r requirements.txt

echo "requirments installed"
# python3 app.py
gunicorn --bind=0.0.0.0 --timeout 0 wsgi:app
# gunicorn  -b  0.0.0.0:${WEBSITES_PORT:-8000} -w  4  --timeout  600  app:app