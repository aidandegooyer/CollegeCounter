import statistics
import time
from flask import Flask, send_from_directory, request
from flask_cors import CORS
import requests
import os
from dotenv import load_dotenv
from PIL import Image
from cc_backend.models import Player, Team, Match
from cc_backend.db import db
import cc_backend.views


app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# For local development, you can start with SQLite:
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///test.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db.init_app(app)


UPLOAD_FOLDER = "static/uploads"
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif"}
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

# Read the .env file and set environment variables

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), ".env"))
FACEIT_API_KEY = os.getenv("FACEIT_API_KEY")
if FACEIT_API_KEY is None:
    raise ValueError("FACEIT_API_KEY not found in the environment variables.")


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
def update_matches():
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
            print(f"Updated match {match.match_id}")
        else:
            print(f"Error updating match {match.match_id}")
    return "Matches updated!"


@app.route("/update_schedule")
def update_schedule():
    one_week_from_now = int(time.time()) + 7 * 24 * 60 * 60
    matches = Match.query.filter(
        Match.scheduled_time > int(time.time()),
        Match.scheduled_time <= one_week_from_now,
        Match.status == "SCHEDULED",
    ).all()
    for match in matches:
        url = f"https://open.faceit.com/data/v4/matches/{match.match_id}"
        headers = {"Authorization": "Bearer " + FACEIT_API_KEY}
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            match_data = response.json()
            if match_data.get("scheduled_at") != match.scheduled_time:
                match.scheduled_time = match_data.get("scheduled_at")
                print(f"Updated match {match.match_id}")
                db.session.commit()
            else:
                print(f"Match {match.match_id} already up to date")

        else:
            print(f"Error updating match {match.match_id}")
    return "Schedule updated!"


@app.route("/inspect_db")
def inspect_db():
    players = Player.query.all()
    teams = Team.query.all()
    matches = Match.query.all()
    return {
        "matches": [match.as_dict() for match in matches],
        "teams": [team.as_dict() for team in teams],
        "players": [player.as_dict() for player in players],
    }


@app.route("/update_all_players_elo")
def update_all_players_elo():
    players = Player.query.all()
    for player in players:
        user_id = player.player_id
        # get the elo number from faceit api at https://open.faceit.com/data/v4/players/{player_id}/games/{game_id}/stats
        headers = {"Authorization": "Bearer 10221230-93bb-4048-9c7b-1183ffe42f90"}
        response = requests.get(
            f"https://open.faceit.com/data/v4/players/{user_id}", headers=headers
        )
        if response.status_code == 200:
            elo = response.json()["games"]["cs2"]["faceit_elo"]
            player.elo = elo
            print(f"Got elo {elo} for user {player.nickname}")

    db.session.commit()
    return "All players' ELO updated!"


@app.route("/calculate_initial_elo")
def calculate_initial_elo():
    teams = Team.query.all()
    for team in teams:
        player_elos = [player.elo for player in team.roster]
        mean_elo = statistics.mean(player_elos)
        std_dev = statistics.stdev(player_elos)
        k = 0.1
        team_elo = mean_elo - k * std_dev
        team.elo = team_elo
        print(f"Calculated ELO for team {team.name}: {team_elo}")
    db.session.commit()
    return "Initial ELO calculated!"


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
def upload_file():
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
        filepath = os.path.join(
            app.config["UPLOAD_FOLDER"], team_id, f"{player_id}.png"
        )

        # Create the directory if it doesn't exist
        os.makedirs(os.path.dirname(filepath), exist_ok=True)

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
        if os.path.exists(filepath):
            os.remove(filepath)
        # Save the image as PNG
        image.save(filepath, "PNG")

        player.avatar = "http://localhost:8889/" + filepath
        db.session.commit()

        return {"message": "File uploaded successfully"}, 200

    return {"error": "File type not allowed"}, 400


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route("/")
def index():
    return "Hello, Flask with SQL database!"


if __name__ == "__main__":
    print(FACEIT_API_KEY)
    create_tables()
    CORS(app)  # Enable CORS for all routes
    # Run on 0.0.0.0 so it’s accessible from Docker
    app.run(host="localhost", port="8889", debug=True)
