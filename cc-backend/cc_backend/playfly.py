import datetime
import json
import requests
from cc_backend import logger
from cc_backend.db import db
from cc_backend.models import Player, Team, Match


def add_playfly_teams_to_db(json_file):
    with open(json_file, "r") as f:
        data = json.load(f)
        for team in data:
            player_id = team["roster"][0]["player_id"]
            url = f"http://127.0.0.1:8889/player/{player_id}"
            response = requests.get(url)
            if response.status_code == 200:
                data = response.json()
                logger.debug(f"Team {team['name']} exists")
                # fetch team from db by using teamid and add playfly id and participant id
                db_team = Team.query.get(data["team_id"])
                db_team.playfly_id = team["playfly_id"]
                db_team.playfly_participant_id = team["playfly_participant_id"]
            else:
                logger.info(f"Team {team['name']} does not exist")
                db_team = Team(
                    team_id=team["team_id"],
                    name=team["name"],
                    leader=team["leader"],
                    avatar=team["avatar"],
                    elo=0,
                    playfly_id=team["playfly_id"],
                    playfly_participant_id=team["playfly_participant_id"],
                )
                db.session.add(db_team)
                db.session.flush()

            logger.debug(f"Team {db_team.name} updated")

        db.session.commit()


def add_playfly_players_to_db(json_file):
    with open(json_file, "r") as f:
        data = json.load(f)
        for team in data:
            team_id = (
                db.session.query(Team.team_id).filter_by(name=team["name"]).first()
            )
            for player in team["roster"]:
                player_id = player["player_id"]
                url = f"http://127.0.0.1:8889/player/{player_id}"
                response = requests.get(url)
                if response.status_code == 200:
                    logger.debug(f"User {player['nickname']} exists")

                else:
                    logger.info(f"User {player['nickname']} does not exist")
                    db_player = Player(
                        player_id=player["player_id"],
                        nickname=player["nickname"],
                        avatar=player["avatar"],
                        skill_level=player["skill_level"],
                        steam_id=player["steam_id"],
                        faceit_id=player["faceit_id"],
                        elo=player["elo"],
                        team_id=team_id[0],
                    )
                    db.session.add(db_player)
                    db.session.flush()

            logger.debug(f"Team {team['name']} updated")

    db.session.commit()


def add_playfly_matches_to_db(json_file):
    with open(json_file, "r") as f:
        data = json.load(f)
        for match in data:
            if len(match["participants"]) != 2:
                logger.debug(
                    f"Match {match['id']} has less than 2 participants (likely a bye week)"
                )
                continue
            team1_participant_id = match["participants"][0]["participantId"]
            team2_participant_id = match["participants"][1]["participantId"]

            # get team ids by querying database for team id
            team1id = db.session.query(Team.team_id).filter_by(
                playfly_participant_id=team1_participant_id
            )
            team2id = db.session.query(Team.team_id).filter_by(
                playfly_participant_id=team2_participant_id
            )

            # convert "2025-02-01T02:00:00Z" to unix timestamp
            time = int(
                datetime.datetime.strptime(match["startTimeUtc"], "%Y-%m-%dT%H:%M:%SZ")
                .replace(tzinfo=datetime.timezone.utc)  # Explicitly set timezone to UTC
                .timestamp()
            )
            playflyurl = f"https://esports.playflycollege.gg/matches/{match['id']}"

            db_match = Match(
                match_id=match["id"],
                game="cs2",
                competition="playfly",
                team1_id=team1id,
                team2_id=team2id,
                scheduled_time=time,
                status="SCHEDULED",
                match_url=playflyurl,
                platform="playfly",
            )
            logger.debug(f"Match {match['id']} added to database")
            db.session.add(db_match)
        db.session.commit()


def update_playfly_match_schedule():
    one_week_from_now = int(datetime.datetime.now().timestamp()) + 7 * 24 * 60 * 60
    matches = Match.query.filter(
        Match.scheduled_time <= one_week_from_now,
        Match.status == "SCHEDULED",
        Match.competition == "playfly",
    ).all()
    logger.info(f"Found {len(matches)} matches to update")
    for match in matches:
        url = f"https://esports.playflycollege.gg/matches/{match.match_id}"
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()
            if data.get("scheduled_at") != match.scheduled_time:
                match.scheduled_time = data.get("scheduled_at")
                logger.debug(f"Match {match.match_id} schedule updated")
            else:
                logger.debug(f"Match {match.match_id} already up to date")

            logger.debug(f"Match {match.match_id} updated")
        else:
            logger.debug(f"Match {match.match_id} not found")
    db.session.commit()


def get_team_image_url(team_id):
    url = f"https://api.leaguespot.gg/api/v1/teams/{team_id}"
    headers = {
        "X-League-Id": "53015f28-5b33-4882-9f8b-16dcbb13deee",
        "X-App": "web",
        "X-Version": "20240912.2",
    }
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        data = response.json()
        return data["logoUrl"]
    else:
        logger.error(f"Failed to fetch team image. Status code: {response.status_code}")


def update_playfly_matches():
    count = 0
    matches = Match.query.filter(
        Match.scheduled_time <= datetime.datetime.now().timestamp(),
        Match.status == "SCHEDULED",
        Match.competition == "playfly",
    ).all()
    logger.info(f"Found {len(matches)} matches to update")

    for match in matches:
        # get team participant ids from database
        team1_participant_id = (
            db.session.query(Team.playfly_participant_id)
            .filter_by(team_id=match.team1_id)
            .first()[0]
        )
        team2_participant_id = (
            db.session.query(Team.playfly_participant_id)
            .filter_by(team_id=match.team2_id)
            .first()[0]
        )
        url = f"https://api.leaguespot.gg/api/v1/matches/{match.match_id}/participants"
        headers = {
            "X-League-Id": "53015f28-5b33-4882-9f8b-16dcbb13deee",
            "X-App": "web",
            "X-Version": "20240912.2",
        }
        response = requests.get(url, headers=headers)
        team1_match_id = None
        team2_match_id = None
        if response.status_code == 200:
            data = response.json()
            for participant in data:
                if participant["participantId"] == team1_participant_id:
                    team1_match_id = participant["id"]
                elif participant["participantId"] == team2_participant_id:
                    team2_match_id = participant["id"]

        else:
            logger.error(
                f"Match {match.match_id} not found, status code: {response.status_code}, {response.text}"
            )
        if not team1_match_id or not team2_match_id:
            logger.error(f"Match {match.match_id} participants not found")
        logger.debug(f"Match {match.match_id} - {team1_match_id} vs {team2_match_id}")
        results = get_results(
            match_id=match.match_id,
            team1=team1_match_id,
            team2=team2_match_id,
            team1participantid=team1_participant_id,
            team2participantid=team2_participant_id,
        )
        if results is None:
            logger.error(f"Match {match.match_id} results not found")
            continue
        if results["team1score"] == results["team2score"] == 0:
            logger.error(f"Match {match.match_id} results not found")
            continue
        if results:
            match.status = "FINISHED"
            match.results_winner = results["winner"]
            match.results_score_team1 = results["team1score"]
            match.results_score_team2 = results["team2score"]
            logger.debug(
                f"Match {match.match_id} results updated, winner: {results['winner']}, score: {results['team1score']} - {results['team2score']}"
            )
            count += 1
        else:
            logger.error(f"Match {match.match_id} results not found")

    db.session.commit()
    return count


def get_results(match_id, team1, team2, team1participantid, team2participantid):
    url = f"https://api.leaguespot.gg/api/v1/matches/{match_id}/games"
    headers = {
        "X-League-Id": "53015f28-5b33-4882-9f8b-16dcbb13deee",
        "X-App": "web",
        "X-Version": "20240912.2",
    }

    response = requests.get(url, headers=headers)
    game_wins = {team1: 0, team2: 0}  # Track wins for both teams

    if response.status_code == 200:
        data = response.json()

        if not data:  # No game data found, check for forfeit
            logger.warning(
                f"No games found for Match ID: {match_id}, checking for forfeit"
            )

            url2 = f"https://api.leaguespot.gg/api/v2/matches/{match_id}"
            response = requests.get(url2, headers=headers)

            if response.status_code == 200:
                data2 = response.json()
                participants = data2["participants"]

                for participant in participants:
                    if participant["hasForfeited"]:
                        logger.debug(
                            f"Match was forfeited by participant {participant['participantId']}"
                        )

                        match_loser = participant["participantId"]
                        match_winner = (
                            "faction2"
                            if match_loser == team1participantid
                            else "faction1"
                        )

                        return {
                            "winner": match_winner,
                            "team1score": 2 if match_winner == "faction1" else 0,
                            "team2score": 2 if match_winner == "faction2" else 0,
                        }
            else:
                logger.error(
                    f"Failed to fetch match data. Status code: {response.status_code} - {response.text}"
                )

            return None  # Return None if no valid result is found

        else:
            for game in data:
                if not game["isComplete"]:
                    continue  # Ignore incomplete games

                # Extract scores
                scores = game["results"][0]["scores"]
                scores_sorted = sorted(scores, key=lambda x: x["score"], reverse=True)
                winner_id = scores_sorted[0]["matchParticipantId"]  # Highest score wins

                # Increment game win count
                if winner_id == team1:
                    game_wins[team1] += 1
                elif winner_id == team2:
                    game_wins[team2] += 1

            # Determine match winner and format return data
            if game_wins[team1] > game_wins[team2]:
                match_winner = "faction1"
            else:
                match_winner = "faction2"

            return {
                "winner": match_winner,
                "team1score": game_wins[team1],
                "team2score": game_wins[team2],
            }

    else:
        logger.error(
            f"Failed to fetch match games. Status code: {response.status_code} - {response.text}"
        )

    return None  # Return None if there was an error
