from flask import Blueprint, abort, send_from_directory, request, current_app
import json
from cc_backend import logger
import time
import requests
from cc_backend.db import db
from cc_backend.models import EloHistory, Player, Team, Match
from functools import wraps
import statistics
import os
from dotenv import load_dotenv
from PIL import Image
from google.cloud import storage
from io import BytesIO


bp = Blueprint("main", __name__)


load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), ".env"))
SECRET_TOKEN = os.environ.get("MY_SECRET_TOKEN")
FACEIT_API_KEY = os.getenv("FACEIT_API_KEY")
if FACEIT_API_KEY is None:
    raise ValueError("FACEIT_API_KEY not found in the environment variables.")
if SECRET_TOKEN is None:
    raise ValueError("SECRET_TOKEN not found in the environment variables.")
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif"}


# Configure logging


def get_faceit_tournament(
    championship_id: str, match_type: str, competition: str, api_key: str
):
    try:
        match_list = []
        offset = 0
        limit = 10
        while True:
            url = f"https://open.faceit.com/data/v4/championships/{championship_id}/matches"
            params = {"type": match_type, "offset": offset, "limit": limit}
            headers = {"Authorization": "Bearer " + api_key}
            response = requests.get(
                url,
                headers=headers,
                params=params,
            )

            if response.status_code == 200:
                batch = response.json()
                print(f"Retrieved {len(batch['items'])} championships")
                if not batch["items"]:
                    break
                match_list.extend(batch["items"])
                offset += 10
            else:
                response.raise_for_status()
    except json.JSONDecodeError:
        print("Error decoding JSON from past.json.")
    except Exception as e:
        print(f"An error occurred: {e}")

    # Get all teams from the JSON
    teams_json = {}
    for match in match_list:
        faction1 = match["teams"]["faction1"]
        faction2 = match["teams"]["faction2"]
        teams_json[faction1["faction_id"]] = faction1
        teams_json[faction2["faction_id"]] = faction2

        # Create teams and attach the players using the dictionary
    teams_dict = {}
    for team in teams_json.values():
        team_id = team["faction_id"]
        # Use no_autoflush when querying for an existing team

        existing_team = Team.query.get(team_id)
        if not existing_team and team_id not in teams_dict:
            db_team = Team(
                team_id=team_id,
                name=team["name"],
                leader=team["leader"],
                avatar=team["avatar"],
                elo=0,
            )

            db.session.add(db_team)
            db.session.flush()

            teams_dict[team_id] = db_team
        else:
            # Use the already persisted team
            teams_dict[team_id] = (
                existing_team if existing_team else teams_dict[team_id]
            )

    # Create players and store them in a dictionary for quick lookup
    #    load players into database
    players_dict = {}
    for team in teams_json.values():
        for player in team["roster"]:
            with db.session.no_autoflush:
                existing_player = Player.query.get(player["player_id"])
            if existing_player is None:
                db_player = Player(
                    player_id=player["player_id"],
                    nickname=player["nickname"],
                    avatar=player["avatar"],
                    skill_level=player["game_skill_level"],
                    steam_id=player["game_player_id"],
                    elo=0,
                    team_id=team["faction_id"],
                )
                db.session.add(db_player)
                db.session.flush()
                players_dict[player["player_id"]] = db_player
            else:
                players_dict[player["player_id"]] = existing_player

    # Create matches and set up team relationships using the teams_dict
    for match in match_list:
        match_id = match["match_id"]
        if not Match.query.get(match_id):
            db_match = Match(
                match_id=match_id,
                game=match["game"],
                competition=competition,
                team1_id=match["teams"]["faction1"]["faction_id"],
                team2_id=match["teams"]["faction2"]["faction_id"],
                scheduled_time=match.get("scheduled_at")
                or match.get("finished_at")
                or 0,
                status=match["status"],
                match_url=match["faceit_url"],
                results_winner=match.get("results", {}).get("winner"),
                results_score_team1=match.get("results", {})
                .get("score", {})
                .get("faction1"),
                results_score_team2=match.get("results", {})
                .get("score", {})
                .get("faction2"),
            )
            # Append the teams using our stored references
            team1_id = match["teams"]["faction1"]["faction_id"]
            team2_id = match["teams"]["faction2"]["faction_id"]
            if team1_id in teams_dict:
                db_match.teams.append(teams_dict[team1_id])
            if team2_id in teams_dict:
                db_match.teams.append(teams_dict[team2_id])
            db.session.add(db_match)
            db.session.flush()

    db.session.commit()


def get_updated_schedule(api_key: str):
    count = 0
    one_week_from_now = int(time.time()) + 7 * 24 * 60 * 60
    matches = Match.query.filter(
        Match.scheduled_time <= one_week_from_now,
        Match.status == "SCHEDULED",
    ).all()
    logger.debug(f"Found {len(matches)} matches to update")
    for match in matches:
        url = f"https://open.faceit.com/data/v4/matches/{match.match_id}"
        headers = {"Authorization": "Bearer " + api_key}
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            match_data = response.json()
            if match_data.get("scheduled_at") != match.scheduled_time:
                match.scheduled_time = match_data.get("scheduled_at")
                logger.info(f"Updated match {match.match_id}")
                count += 1
                db.session.commit()
            else:
                logger.debug(f"Match {match.match_id} already up to date")

        else:
            logger.error(f"Error updating match {match.match_id}")
    return count


def require_token(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Check for the token in a query parameter or in the headers
        token = request.args.get("token") or request.headers.get("X-Secret-Token")
        if current_app.debug:
            return f(*args, **kwargs)

        if not token or token != SECRET_TOKEN:
            abort(403)  # Forbidden if token doesn't match
        return f(*args, **kwargs)

    return decorated_function


@bp.route("/create_tables")
@require_token
def create_tables():
    with current_app.app_context():
        db.create_all()


@bp.route("/get_all_matches")
def get_all_matches():
    get_faceit_tournament(
        championship_id="62554deb-7401-4e35-ae05-8ee04e1bf9e2",
        match_type="all",
        competition="necc",
        api_key=FACEIT_API_KEY,
    )
    return "Matches updated!"


@bp.route("/update_matches")
@require_token
def update_matches():
    logger.debug("Updating matches")
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


@bp.route("/update_schedule")
@require_token
def update_schedule():
    logger.debug("Updating schedule")

    count = get_updated_schedule(api_key=FACEIT_API_KEY)
    return f"Schedule for {count} matches updated! "


@bp.route("/inspect_db")
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


@bp.route("/update_all_players_elo")
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


@bp.route("/clear_elo_history")
@require_token
def clear_elo_history():
    EloHistory.query.delete()
    db.session.commit()
    return "ELO history cleared!"


@bp.route("/calculate_initial_elo")
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


@bp.route("/update_all_elo")
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


@bp.route("/update")
@require_token
def update():
    matches = update_matches()
    schedule = update_schedule()
    elo = update_all_elo()
    return f"{matches} | {schedule} | {elo}"


@bp.route("/get_elo_history")
def get_elo_history():
    elo_history = EloHistory.query.all()
    return [entry.as_dict() for entry in elo_history]


@bp.route("/player/<player_id>")
def get_player(player_id):
    player = Player.query.get(player_id)
    return player.as_dict() if player else "Player not found"


@bp.route("/team/<team_id>")
def get_team(team_id):
    team = Team.query.get(team_id)
    return team.as_dict() if team else "Team not found"


@bp.route("/teams")
def get_teams():
    teams = Team.query.all()
    return [team.as_dict() for team in teams]


@bp.route("/team/<team_id>/matches")
def get_team_matches(team_id):
    team = Team.query.get(team_id)
    return (
        [match.as_dict() for match in team.matches]
        if team
        else {"error": "Team not found"}
    )


@bp.route("/team/<team_id>/players")
def get_team_players(team_id):
    team = Team.query.get(team_id)
    return (
        [player.as_dict() for player in team.roster]
        if team
        else {"error": "Team not found"}
    )


@bp.route("/team/<team_id>/rank")
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


@bp.route("/match/<match_id>")
def get_match(match_id):
    match = Match.query.get(match_id)
    return match.as_dict() if match else "Match not found"


@bp.route("/upcoming")
def get_upcoming():
    matches = Match.query.filter_by(status="SCHEDULED").all()
    return [match.as_dict() for match in matches]


@bp.route("/upcoming/<num>")
def get_upcoming_num(num):
    matches = (
        Match.query.filter_by(status="SCHEDULED")
        .order_by(Match.scheduled_time)
        .limit(4)
        .all()
    )
    return [match.as_dict() for match in matches]


@bp.route("/results")
def get_results():
    matches = Match.query.filter_by(status="FINISHED").all()
    return [match.as_dict() for match in matches]


@bp.route("/top10")
def get_top10():
    teams = Team.query.order_by(Team.elo.desc()).limit(10).all()
    return [team.as_dict() for team in teams]


@bp.route("/static/<path:filename>")
def serve_static(filename):
    return send_from_directory("static", filename)


@bp.route("/upload_profile_pic", methods=["POST"])
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
        bucket_name = current_app.config["BUCKET_NAME"]
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


@bp.route("/upload_team_photo", methods=["POST"])
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
        bucket_name = current_app.config["BUCKET_NAME"]
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


@bp.route("/")
def index():
    return "Hello, Flask with SQL database!"
