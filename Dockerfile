FROM python:3.11-slim

WORKDIR /app

# Install dependencies
RUN pip install --no-cache-dir fastapi "uvicorn[standard]" aiosqlite bcrypt python-multipart

# Copy application code
COPY web_counter/ ./web_counter/
COPY pyproject.toml .

# Install package in development mode
RUN pip install -e .

# Create data directory
RUN mkdir -p /app/data

EXPOSE 8000

ENV COUNTER_HOST=0.0.0.0
ENV COUNTER_PORT=8000
ENV COUNTER_DB_PATH=/app/data/counter.db
ENV COUNTER_PID_FILE=/app/data/counter.pid

CMD ["python", "-m", "uvicorn", "web_counter.main:app", "--host", "0.0.0.0", "--port", "8000"]
