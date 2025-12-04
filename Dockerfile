# Use python:3.11-slim for better compatibility/stability than Alpine
FROM python:3.11-slim

# Create a volume point for persistent data
VOLUME /app/data

WORKDIR /app

# Copy requirements FIRST (Docker caching optimization)
# This way, if you change main.py, it doesn't re-download all libraries
COPY requirements.txt .

# Install dependencies from the file
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application
COPY main.py .
COPY flo_client ./flo_client

# Ensure data directory exists (just in case)
RUN mkdir -p /app/data

# Run unbuffered so logs show up immediately in Proxmox
ENTRYPOINT ["python", "-u", "main.py"]