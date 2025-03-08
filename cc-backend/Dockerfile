# Use an official Python runtime as a parent image
FROM python:3.13-slim

# Set the working directory in the container
WORKDIR /cc-backend

# Copy the requirements file and install dependencies
COPY requirements.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code
COPY . .

EXPOSE 8889

# Define the command to run the app
CMD ["gunicorn", "--workers", "4", "--bind", "0.0.0.0:8889", "app:app"]