# Use an official Python runtime as a parent image
FROM python:3.11-slim

# Set the working directory in the container
WORKDIR /app

# Install system dependencies that might be needed for some Python packages
# (e.g., build-essential for packages with C extensions)
# Add other dependencies if needed for specific doc/pdf libraries
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy the requirements file into the container at /app
COPY ./requirements.txt /app/

# Install any needed packages specified in requirements.txt
# Ensure pip is up-to-date
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code into the container at /app
# Ensure the app directory exists in your project root alongside the Dockerfile
COPY ./app /app/app

# Make port 8000 available to the world outside this container
EXPOSE 8000

# Define environment variable for the Gemini API Key (will be passed at runtime)
# This line just declares that the container expects this variable.
ENV GEMINI_API_KEY=""

# Define module name for uvicorn (optional, can be useful)
ENV MODULE_NAME="app.main"
ENV VARIABLE_NAME="app"

# Run app.main:app when the container launches using uvicorn
# Use 0.0.0.0 to ensure it's accessible from outside the container
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

