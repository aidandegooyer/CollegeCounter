# Use the official Python runtime image
FROM python:3.13.7-alpine

# Create the app directory
RUN mkdir /app

# Set the working directory inside the container
WORKDIR /app

# Set environment variables 
# Prevents Python from writing pyc files to disk
ENV PYTHONDONTWRITEBYTECODE=1
#Prevents Python from buffering stdout and stderr
ENV PYTHONUNBUFFERED=1 

# Upgrade pip
RUN pip install --upgrade pip 

# Copy the Django project  and install dependencies
COPY requirements.txt  /app/

# run this command to install all dependencies 
# python deps
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt gunicorn psycopg2-binary

# app
COPY . .

# gunicorn config
COPY gunicorn.conf.py .

EXPOSE 8000
CMD ["gunicorn", "--config", "gunicorn.conf.py", "backend.wsgi:application"]