# Use an official Python runtime as a parent image
FROM python:3.13-slim

# Set the working directory in the container
WORKDIR /cc-backend

# Copy the requirements file and install dependencies
COPY requirements.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code
COPY . .

# Copy the static files
COPY static /app/static

# Copy the uploads directory
COPY static/uploads /app/static/uploads

# Expose port 5000 for the Flask app
EXPOSE 5000

# Define the command to run the app
CMD ["python", "app.py"]