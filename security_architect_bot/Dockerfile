# Use a stable Python base image
FROM python:3.12-slim

# Set the working directory in the container
WORKDIR /app

# Copy requirements.txt first for efficient caching
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Install Tesseract and its language packs (example: English)
RUN apt-get update && apt-get install -y tesseract-ocr libtesseract-dev \
    && apt-get install -y tesseract-ocr-eng

# Copy the rest of the application code to the container
COPY . .

# Run the application
CMD [ "python", "-u", "slack_analyzer.py" ]
