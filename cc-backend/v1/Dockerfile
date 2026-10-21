# Use the official Python runtime image
FROM python:3.15.0-alpine

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

# The commit and time this image was built from (scripts/deploy-prod.sh), for
# /v1/public/version and the API docs. After the pip install so a new commit
# doesn't reinstall dependencies.
ARG GIT_SHA=dev
ARG BUILD_DATE=
ENV GIT_SHA=$GIT_SHA
ENV BUILD_DATE=$BUILD_DATE

# gunicorn config
COPY gunicorn.conf.py .

# Runs migrations before starting gunicorn
RUN chmod +x entrypoint.sh

EXPOSE 8000
ENTRYPOINT ["./entrypoint.sh"]
CMD ["gunicorn", "--config", "gunicorn.conf.py", "v1.wsgi:application"]
