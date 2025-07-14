# Use official Python 3.11 slim image
FROM python:3.11-slim

# Set working directory inside the container
WORKDIR /app

# Copy all project files to the container
COPY . /app

# Upgrade pip and install dependencies
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

# Expose the port your Flask app runs on (if needed)
EXPOSE 5000

# Run your Flask app
CMD ["python", "flask_app.py"]
