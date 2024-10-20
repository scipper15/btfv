FROM python:3.12

WORKDIR /app

# Set PYTHONPATH to include /app so that Python can find /app/src
ENV PYTHONPATH=/app

# Install dependencies
COPY pyproject.toml poetry.lock* /app/
RUN pip install --upgrade pip
RUN pip install poetry && \
    poetry install --no-interaction --no-ansi

# Copy the source code
COPY src/ /app/src/

# Expose the Flask port
EXPOSE 5000
