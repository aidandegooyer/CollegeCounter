from cc_backend.db import db


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
