#!/bin/bash
echo "Starting the application"
python  -m  pip  install  --upgrade  pip
pip  install  -r  requirements.txt

echo "requirments installed"
python3 app.py