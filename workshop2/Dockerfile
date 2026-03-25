# Dockerfile
FROM python:3.11-slim

WORKDIR /app

# Copy consumer script
COPY consumer.py .

# Install dependencies
RUN pip install pika

# Command to run
CMD ["python", "consumer.py"]
