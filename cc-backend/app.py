import json
import statistics
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
import requests

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# For local development, you can start with SQLite:
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///test.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)


class Player(db.Model):
    def as_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}

    player_id = db.Column(db.String, primary_key=True)
    nickname = db.Column(db.String, nullable=False)
    avatar = db.Column(db.String, nullable=True)
    skill_level = db.Column(db.Integer, nullable=False)
    steam_id = db.Column(db.String, nullable=True)
    elo = db.Column(db.Integer, nullable=False)
    team_id = db.Column(
        db.String, db.ForeignKey("team.team_id"), nullable=False
    )  # Add foreign key to enforce one-to-many relationship


class Team(db.Model):
    def as_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}

    team_id = db.Column(db.String, primary_key=True)
    name = db.Column(db.String, nullable=False)
    leader = db.Column(db.String, nullable=False)
    avatar = db.Column(db.String, nullable=True)
    elo = db.Column(db.Integer, nullable=False)
    roster = db.relationship(
        "Player", backref="team"
    )  # Remove secondary and use backref
    matches = db.relationship("Match", secondary="team_match", back_populates="teams")


class Match(db.Model):
    def as_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}

    match_id = db.Column(db.String, primary_key=True)
    game = db.Column(db.String, nullable=False)
    competition = db.Column(db.String, nullable=False)
    team1_id = db.Column(db.String, db.ForeignKey("team.team_id"), nullable=False)
    team2_id = db.Column(db.String, db.ForeignKey("team.team_id"), nullable=False)
    scheduled_time = db.Column(db.Integer, nullable=False)
    status = db.Column(db.String, nullable=False)
    match_url = db.Column(db.String, nullable=True)
    results_winner = db.Column(db.String, nullable=True)
    results_score_team1 = db.Column(db.Integer, nullable=True)
    results_score_team2 = db.Column(db.Integer, nullable=True)
    teams = db.relationship("Team", secondary="team_match", back_populates="matches")


team_match = db.Table(
    "team_match",
    db.Column("team_id", db.String, db.ForeignKey("team.team_id"), primary_key=True),
    db.Column("match_id", db.String, db.ForeignKey("match.match_id"), primary_key=True),
)


def get_faceit_tournament(championship_id: str, match_type: str, competition: str):
    try:
        match_list = []
        offset = 0
        limit = 10
        while True:
            url = f"https://open.faceit.com/data/v4/championships/{championship_id}/matches"
            params = {"type": match_type, "offset": offset, "limit": limit}
            headers = {"Authorization": "Bearer 10221230-93bb-4048-9c7b-1183ffe42f90"}
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
                players_dict[player["player_id"]] = db_player
            else:
                players_dict[player["player_id"]] = existing_player

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
            existing_player_ids = {p.player_id for p in db_team.roster}
            for player in team["roster"]:
                player_id = player["player_id"]
                # Only append if not already in the roster
                if player_id not in existing_player_ids:
                    print(f"Adding player {player_id} to team {team_id}")
                    db_team.roster.append(players_dict[player_id])
                    existing_player_ids.add(player_id)
                else:
                    print(f"Player {player_id} already in team {team_id}")
            db.session.add(db_team)
            teams_dict[team_id] = db_team
        else:
            # Use the already persisted team
            teams_dict[team_id] = (
                existing_team if existing_team else teams_dict[team_id]
            )

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

    db.session.commit()


def create_tables():
    with app.app_context():
        db.create_all()


@app.route("/update_matches")
def update_matches():
    get_faceit_tournament(
        championship_id="62554deb-7401-4e35-ae05-8ee04e1bf9e2",
        match_type="all",
        competition="necc",
    )
    return "Matches updated!"


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


@app.route("/")
def index():
    return "Hello, Flask with SQL database!"


if __name__ == "__main__":
    create_tables()
    CORS(app)  # Enable CORS for all routes
    # Run on 0.0.0.0 so it’s accessible from Docker
    app.run(host="localhost", port="8889", debug=True)
