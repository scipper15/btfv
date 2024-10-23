#!/bin/bash

set -e

cleanup() {
  echo "Script finished. Press Enter to close."
  read
}
trap cleanup EXIT

# Load environment variables from .env file
if [ -f .env ]; then
    echo "Loading environment variables from .env..."
    export $(grep -v '^#' .env | xargs)
else
    echo ".env file not found"
    exit 1
fi

# Detect which service is running (based on service name passed in as argument)
SERVICE=$1

# Check if SERVICE is empty
if [ -z "$SERVICE" ]; then
    echo "Error: No service provided. Usage: ./entrypoint.sh <service>"
    exit 1
fi

echo "Starting $SERVICE service..."

# Perform service-specific logic based on the argument passed
case "$SERVICE" in

  web)
    echo "Running web service..."
    # Start the Flask web server (for web service)
    exec poetry run gunicorn "web_main:app" --bind 0.0.0.0:8000 --workers 4
    ;;

  scraper)
    echo "Running scraper service..."
    # Start the scraper (for scraper service)
    exec poetry run python /app/src/scraper_main.py
    ;;

  *)
    echo "Unknown service: $SERVICE"
    exit 1
    ;;
esac
