from flask import current_app, Blueprint
import json
import logging
import time
import requests
from cc_backend.db import db
from cc_backend.models import Player, Team, Match

bp = Blueprint("main", __name__)


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


with current_app.app_context():
    logger = logging.getLogger(__name__)
    logger.setLevel(getattr(logging, current_app.config.get["LOG_LEVEL"]))
    ch = logging.StreamHandler()
    ch.setLevel(getattr(logging, current_app.config.get["LOG_LEVEL"]))
    ch.setFormatter(CustomFormatter())
    logger.addHandler(ch)


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
        Match.scheduled_time > int(time.time()),
        Match.scheduled_time <= one_week_from_now,
        Match.status == "SCHEDULED",
    ).all()
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
