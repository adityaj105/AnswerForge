# answerforge/sandbox/Dockerfile
FROM python:3.12-slim

# Create a non-root user for safety
RUN useradd -m sandboxuser

# Set working directory
WORKDIR /sandbox

# Copy requirements if you want to test with libraries (optional)
# COPY requirements.txt .
# RUN pip install --no-cache-dir -r requirements.txt

# Run as non-root
USER sandboxuser

# Default command: nothing; code will be passed dynamically
CMD ["python3"]
