from flask import Flask
from flask_cors import CORS
import os
from cc_backend import logger
from dotenv import load_dotenv
from cc_backend.db import db
import argparse
from cc_backend.views import bp


is_dev = False


app = Flask(__name__)


app.register_blueprint(bp)

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), ".env"))

# For local development, you can start with SQLite:

if is_dev:
    logger.info("Running in development mode. Using SQLite local DB.")
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///test.db"
    CORS(app)
else:
    logger.warning(
        "Running in production mode. THIS IS NOT RECOMMENDED FOR DEVELOPMENT."
    )
    app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("SQLALCHEMY_DATABASE_URI")
    CORS(
        app,
        resources={
            r"/*": {
                "origins": [
                    "https://collegecounter.org",
                    "https://api.collegecounter.org",
                    "https://www.collegecounter.org",
                ]
            }
        },
    )


app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db.init_app(app)


UPLOAD_FOLDER = "static/uploads"
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif"}
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["BUCKET_NAME"] = "cc-static"

GOOGLE_APPLICATION_CREDENTIALS = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")

# Read the .env file and set environment variables

FACEIT_API_KEY = os.getenv("FACEIT_API_KEY")
SECRET_TOKEN = os.environ.get("MY_SECRET_TOKEN")
app.config["SECRET_TOKEN"] = SECRET_TOKEN
app.config["FACEIT_API_KEY"] = FACEIT_API_KEY
if FACEIT_API_KEY is None:
    raise ValueError("FACEIT_API_KEY not found in the environment variables.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="CollegeCounter Backend")
    parser.add_argument("--dev", action="store_true", help="Run in development mode")
    parser.add_argument(
        "--log",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default="INFO",
        help="Set the logging level",
    )
    args = parser.parse_args()

    is_dev = args.dev
    app.config["DEV"] = args.dev
    LOG_LEVEL = args.log

    # CORS(app)  # Enable CORS for all routes

    CORS(
        app,
        resources={
            r"/*": {
                "origins": [
                    "https://collegecounter.org",
                    "https://api.collegecounter.org",
                    "https://www.collegecounter.org",
                ]
            }
        },
    )
    app.run(host="0.0.0.0", port=8889, debug=args.dev)
