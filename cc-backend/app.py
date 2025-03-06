from functools import wraps
import statistics
import time
from flask import Flask, abort, send_from_directory, request
from flask_cors import CORS
import requests
import os
from dotenv import load_dotenv
from PIL import Image
from cc_backend.models import Player, Team, Match, EloHistory
from cc_backend.db import db
from google.cloud import storage
from io import BytesIO
import argparse
import logging


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


# Configure logging
class CustomFormatter(logging.Formatter):
    grey = "\x1b[38m"
    yellow = "\x1b[33m"
    red = "\x1b[31m"
    bold_red = "\x1b[31;1m"
    cyan = "\x1b[36m"
    reset = "\x1b[0m"

    FORMATS = {
        logging.DEBUG: grey + "%(levelname)s - %(message)s" + reset,
        logging.INFO: cyan + "%(levelname)s - %(message)s" + reset,
        logging.WARNING: yellow + "%(levelname)s - %(message)s" + reset,
        logging.ERROR: red + "%(levelname)s - %(message)s" + reset,
        logging.CRITICAL: bold_red + "%(levelname)s - %(message)s" + reset,
    }

    def format(self, record):
        log_fmt = self.FORMATS.get(record.levelno)
        formatter = logging.Formatter(log_fmt)
        return formatter.format(record)


logger = logging.getLogger(__name__)
logger.setLevel(getattr(logging, args.log))
ch = logging.StreamHandler()
ch.setLevel(getattr(logging, args.log))
ch.setFormatter(CustomFormatter())
logger.addHandler(ch)


app = Flask(__name__)

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), ".env"))

# For local development, you can start with SQLite:

if is_dev:
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///test.db"
    CORS(app)
else:
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

app.config["DEV"] = args.dev
app.config["LOG_LEVEL"] = args.log


UPLOAD_FOLDER = "static/uploads"
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif"}
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["BUCKET_NAME"] = "cc-static"

GOOGLE_APPLICATION_CREDENTIALS = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")

# Read the .env file and set environment variables

FACEIT_API_KEY = os.getenv("FACEIT_API_KEY")
SECRET_TOKEN = os.environ.get("MY_SECRET_TOKEN")
if FACEIT_API_KEY is None:
    raise ValueError("FACEIT_API_KEY not found in the environment variables.")

import cc_backend.views  # noqa: E402


def require_token(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Check for the token in a query parameter or in the headers
        token = request.args.get("token") or request.headers.get("X-Secret-Token")
        if not token or token != SECRET_TOKEN:
            abort(403)  # Forbidden if token doesn't match
        return f(*args, **kwargs)

    return decorated_function


def create_tables():
    with app.app_context():
        db.create_all()


@app.route("/get_all_matches")
def get_all_matches():
    cc_backend.views.get_faceit_tournament(
        championship_id="62554deb-7401-4e35-ae05-8ee04e1bf9e2",
        match_type="all",
        competition="necc",
        api_key=FACEIT_API_KEY,
    )
    return "Matches updated!"


@app.route("/update_matches")
@require_token
def update_matches():
    count = 0
    # get all matches that are scheduled with a time before now
    matches = Match.query.filter(
        Match.scheduled_time < int(time.time()), Match.status == "SCHEDULED"
    ).all()
    for match in matches:
        url = f"https://open.faceit.com/data/v4/matches/{match.match_id}"
        headers = {"Authorization": "Bearer " + FACEIT_API_KEY}
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            match_data = response.json()
            match.status = match_data["status"]
            match.results_winner = match_data.get("results", {}).get("winner")
            match.results_score_team1 = (
                match_data.get("results", {}).get("score", {}).get("faction1")
            )
            match.results_score_team2 = (
                match_data.get("results", {}).get("score", {}).get("faction2")
            )
            db.session.commit()
            logger.info(f"Updated match {match.match_id}")
            count += 1
        else:
            logger.error(f"Error updating match {match.match_id}")
    return f"Results for {count} matches updated!"


@app.route("/update_schedule")
@require_token
def update_schedule():
    count = cc_backend.views.get_updated_schedule(api_key=FACEIT_API_KEY)
    return f"Schedule for {count} matches updated! "


@app.route("/inspect_db")
@require_token
def inspect_db():
    players = Player.query.all()
    teams = Team.query.all()
    matches = Match.query.all()
    elo_history = EloHistory.query.all()
    return {
        "matches": [match.as_dict() for match in matches],
        "teams": [team.as_dict() for team in teams],
        "players": [player.as_dict() for player in players],
        "elo_history": [entry.as_dict() for entry in elo_history],
    }


@app.route("/update_all_players_elo")
@require_token
def update_all_players_elo():
    players = Player.query.all()
    for player in players:
        user_id = player.player_id
        # get the elo number from faceit api at https://open.faceit.com/data/v4/players/{player_id}/games/{game_id}/stats
        headers = {"Authorization": "Bearer " + FACEIT_API_KEY}
        response = requests.get(
            f"https://open.faceit.com/data/v4/players/{user_id}", headers=headers
        )
        if response.status_code == 200:
            elo = response.json()["games"]["cs2"]["faceit_elo"]
            player.elo = elo
            logger.debug(f"Got elo {elo} for user {player.nickname}")
        else:
            logger.warning(f"Error getting elo for user {player.nickname}")

    db.session.commit()
    return "All players' ELO updated!"


@app.route("/clear_elo_history")
@require_token
def clear_elo_history():
    EloHistory.query.delete()
    db.session.commit()
    return "ELO history cleared!"


@app.route("/calculate_initial_elo")
@require_token
def calculate_initial_elo():
    teams = Team.query.all()
    for team in teams:
        player_elos = [player.elo for player in team.roster]
        # take the highest 5 elos for this average
        player_elos.sort(reverse=True)
        player_elos = player_elos[:5]
        mean_elo = statistics.mean(player_elos)
        std_dev = statistics.stdev(player_elos)
        k = 0.1
        team_elo = mean_elo - k * std_dev
        team.elo = team_elo
        logger.info(f"Calculated ELO for team {team.name}: {team_elo}")

        elo_history_initial = EloHistory(
            team_id=team.team_id,
            elo=team_elo,
            match_id=None,
            timestamp=0,
        )
        db.session.add(elo_history_initial)

    db.session.commit()
    return "Initial ELO calculated!"


@app.route("/update_all_elo")
@require_token
def update_all_elo():
    # ensure match isnt already updated by checking if matchid is in elo history
    count = 0
    matches = Match.query.filter(
        Match.status == "FINISHED",
        ~Match.match_id.in_(
            db.session.query(EloHistory.match_id).filter(
                EloHistory.match_id.isnot(None)
            )
        ),
    ).all()
    sorted_matches = sorted(matches, key=lambda x: x.scheduled_time)
    for match in sorted_matches:
        update_elo(match)
        logger.info(f"Updated ELO for match {match.match_id}")
        count += 1
    return f"Updated ELO for {count} matches!"


def update_elo(match: Match):
    team1 = Team.query.get(match.team1_id)
    team2 = Team.query.get(match.team2_id)
    if match.results_winner == "faction1":
        team1_new_elo = calculate_new_elo(team1.elo, team2.elo, 1)
        team2_new_elo = calculate_new_elo(team2.elo, team1.elo, 0)
    else:
        team1_new_elo = calculate_new_elo(team1.elo, team2.elo, 0)
        team2_new_elo = calculate_new_elo(team2.elo, team1.elo, 1)
    # create elo history entries
    elo_history_team1 = EloHistory(
        team_id=team1.team_id,
        elo=team1_new_elo,
        match_id=match.match_id,
        timestamp=match.scheduled_time,
    )
    elo_history_team2 = EloHistory(
        team_id=team2.team_id,
        elo=team2_new_elo,
        match_id=match.match_id,
        timestamp=match.scheduled_time,
    )
    db.session.add(elo_history_team1)
    db.session.add(elo_history_team2)
    team1.elo = team1_new_elo
    team2.elo = team2_new_elo
    db.session.commit()


def calculate_new_elo(current_elo, opponent_elo, result):
    k = 150  # K-factor, determines the maximum possible adjustment per game
    expected_score = 1 / (1 + 10 ** ((opponent_elo - current_elo) / 600))
    new_elo = current_elo + k * (result - expected_score)
    return new_elo


@app.route("/update")
@require_token
def update():
    matches = update_matches()
    schedule = update_schedule()
    elo = update_all_elo()
    return f"{matches} | {schedule} | {elo}"


@app.route("/get_elo_history")
def get_elo_history():
    elo_history = EloHistory.query.all()
    return [entry.as_dict() for entry in elo_history]


@app.route("/player/<player_id>")
def get_player(player_id):
    player = Player.query.get(player_id)
    return player.as_dict() if player else "Player not found"


@app.route("/team/<team_id>")
def get_team(team_id):
    team = Team.query.get(team_id)
    return team.as_dict() if team else "Team not found"


@app.route("/teams")
def get_teams():
    teams = Team.query.all()
    return [team.as_dict() for team in teams]


@app.route("/team/<team_id>/matches")
def get_team_matches(team_id):
    team = Team.query.get(team_id)
    return (
        [match.as_dict() for match in team.matches]
        if team
        else {"error": "Team not found"}
    )


@app.route("/team/<team_id>/players")
def get_team_players(team_id):
    team = Team.query.get(team_id)
    return (
        [player.as_dict() for player in team.roster]
        if team
        else {"error": "Team not found"}
    )


@app.route("/team/<team_id>/rank")
def get_team_rank(team_id):
    # get current rank of team, we have to get all teams to do this.
    # TODO: FIX THIS, MAYBE ADD A RANK COLUMN TO TEAM TABLE
    teams = Team.query.all()
    teams.sort(key=lambda x: x.elo, reverse=True)
    rank = 1
    for team in teams:
        if team.team_id == team_id:
            break
        rank += 1
    return {"rank": rank}


@app.route("/match/<match_id>")
def get_match(match_id):
    match = Match.query.get(match_id)
    return match.as_dict() if match else "Match not found"


@app.route("/upcoming")
def get_upcoming():
    matches = Match.query.filter_by(status="SCHEDULED").all()
    return [match.as_dict() for match in matches]


@app.route("/upcoming/<num>")
def get_upcoming_num(num):
    matches = (
        Match.query.filter_by(status="SCHEDULED")
        .order_by(Match.scheduled_time)
        .limit(4)
        .all()
    )
    return [match.as_dict() for match in matches]


@app.route("/results")
def get_results():
    matches = Match.query.filter_by(status="FINISHED").all()
    return [match.as_dict() for match in matches]


@app.route("/top10")
def get_top10():
    teams = Team.query.order_by(Team.elo.desc()).limit(10).all()
    return [team.as_dict() for team in teams]


@app.route("/static/<path:filename>")
def serve_static(filename):
    return send_from_directory("static", filename)


@app.route("/upload_profile_pic", methods=["POST"])
@require_token
def upload_profile_pic():
    if "file" not in request.files:
        return {"error": "No file part"}, 400

    file = request.files["file"]
    if file.filename == "":
        return {"error": "No selected file"}, 400

    if file and allowed_file(file.filename):
        player_id = request.form.get("player_id")
        player = Player.query.get(player_id)
        if not player:
            return {"error": "Player not found"}, 404

        team_id = player.team_id

        image = Image.open(file)
        image = image.convert("RGBA")

        # Crop the image to a square
        width, height = image.size
        new_size = min(width, height)
        left = (width - new_size) / 2
        top = (height - new_size) / 2
        right = (width + new_size) / 2
        bottom = (height + new_size) / 2
        image = image.crop((left, top, right, bottom))

        # Resize the image to 400x400
        image = image.resize((400, 400))

        buffer = BytesIO()
        image.save(buffer, "PNG")
        buffer.seek(0)

        # Upload the image to Google Cloud Storage
        client = storage.Client()
        bucket_name = app.config["BUCKET_NAME"]
        bucket = client.get_bucket(bucket_name)
        blob_path = f"static/uploads/{team_id}/{player_id}.png"
        blob = bucket.blob(blob_path)
        blob.upload_from_file(buffer, content_type="image/png")

        # With uniform bucket-level access, you control public access via IAM, so no need to call blob.make_public()
        # Instead, construct the public URL manually:
        public_url = f"https://storage.googleapis.com/{bucket_name}/{blob_path}"
        player.avatar = public_url
        db.session.commit()

        return {"message": "File uploaded successfully"}, 200

    return {"error": "File type not allowed"}, 400


@app.route("/upload_team_photo", methods=["POST"])
@require_token
def upload_team_photo():
    if "file" not in request.files:
        return {"error": "No file part"}, 400

    type = request.args.get("type")

    file = request.files["file"]
    if file.filename == "":
        return {"error": "No selected file"}, 400

    if file and allowed_file(file.filename):
        team_id = request.form.get("team_id")
        team = Team.query.get(team_id)
        if not team:
            return {"error": "Team not found"}, 404

        image = Image.open(file)
        image = image.convert("RGBA")

        if type == "logo":
            image = image.resize((400, 400))

        buffer = BytesIO()
        image.save(buffer, "PNG")
        buffer.seek(0)

        # Upload the image to Google Cloud Storage
        client = storage.Client()
        bucket_name = app.config["BUCKET_NAME"]
        bucket = client.get_bucket(bucket_name)
        if type == "logo":
            blob_path = f"static/uploads/{team_id}/logo.png"
        elif type == "bg":
            blob_path = f"static/bg/{team_id}.png"
        else:
            return {"error": "Invalid type"}, 400
        blob = bucket.blob(blob_path)
        blob.upload_from_file(buffer, content_type="image/png")

        # With uniform bucket-level access, you control public access via IAM, so no need to call blob.make_public()
        # Instead, construct the public URL manually:
        if type == "logo":
            public_url = f"https://storage.googleapis.com/{bucket_name}/{blob_path}"
            team.avatar = public_url
            db.session.commit()

        return {"message": "File uploaded successfully"}, 200

    return {"error": "File type not allowed"}, 400


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route("/")
def index():
    return "Hello, Flask with SQL database!"


if __name__ == "__main__":
    create_tables()

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
    app.run(host="0.0.0.0", port=8889, debug=True)
