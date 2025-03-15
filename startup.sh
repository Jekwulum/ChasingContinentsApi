#!/bin/bash
echo "Starting the application"
python  -m  pip  install  --upgrade  pip
pip  install  -r  requirements.txt

echo "requirments installed"
# python3 app.py
gunicorn --bind=0.0.0.0 --timeout 0 app:app