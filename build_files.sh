#!/bin/bash
echo "Installing dependencies..."
python3 -m pip install -r requirements.txt

echo "Running migrations..."
python3 manage.py migrate --noinput

echo "Collecting static files..."
python3 manage.py collectstatic --noinput --clear

echo "Seeding starter songs if empty..."
python3 manage.py seed_songs

echo "Build completed successfully!"
