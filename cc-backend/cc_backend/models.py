from cc_backend.db import db


class Player(db.Model):
    def as_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}

    player_id = db.Column(db.String, primary_key=True)
    nickname = db.Column(db.String, nullable=False)
    avatar = db.Column(db.String, nullable=True)
    skill_level = db.Column(db.Integer, nullable=False)
    steam_id = db.Column(db.String, nullable=True)
    faceit_id = db.Column(db.String, nullable=True)
    elo = db.Column(db.Integer, nullable=False)
    visible = db.Column(db.Boolean, nullable=False)
    bench = db.Column(db.Boolean, nullable=False)
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
    playfly_id = db.Column(db.String, nullable=True)
    playfly_participant_id = db.Column(db.String, nullable=True)
    faceit_id = db.Column(db.String, nullable=True)
    school_name = db.Column(db.String, nullable=True)
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
    platform = db.Column(db.String, nullable=False)
    teams = db.relationship("Team", secondary="team_match", back_populates="matches")


class Event(db.Model):
    def as_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}

    __tablename__ = "event"
    event_id = db.Column(db.String, primary_key=True)
    title = db.Column(db.String, nullable=False)
    description = db.Column(db.String, nullable=True)
    start_date = db.Column(db.Integer, nullable=False)
    end_date = db.Column(db.Integer, nullable=False)
    # Assuming each event has one winner
    winner_id = db.Column(db.String, db.ForeignKey("team.team_id"), nullable=True)
    winner = db.relationship("Team", backref="won_events", uselist=False)
    bracket = db.relationship("EventMatch", backref="event", lazy=True)


class EventMatch(db.Model):
    def as_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}

    __tablename__ = "eventmatch"
    id = db.Column(db.String, primary_key=True)
    # Assuming each match is linked to a Match table with an id column
    match_id = db.Column(db.String, db.ForeignKey("match.match_id"), nullable=True)
    match = db.relationship("Match", backref="event_match", lazy=True)
    round = db.Column(db.String, nullable=False)
    number_in_bracket = db.Column(db.Integer, nullable=False)
    event_id = db.Column(db.String, db.ForeignKey("event.event_id"), nullable=False)
    isbye = db.Column(db.Boolean, nullable=False)
    bye_team_id = db.Column(db.String, nullable=True)


class EloHistory(db.Model):
    def as_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}

    id = db.Column(db.Integer, primary_key=True)
    team_id = db.Column(db.String, db.ForeignKey("team.team_id"), nullable=False)
    elo = db.Column(db.Integer, nullable=False)
    match_id = db.Column(db.String, db.ForeignKey("match.match_id"), nullable=False)
    timestamp = db.Column(db.Integer, nullable=False)


team_elo_history = db.Table(
    "team_elo_history",
    db.Column("team_id", db.String, db.ForeignKey("team.team_id"), primary_key=True),
    db.Column(
        "elo_history_id", db.Integer, db.ForeignKey("elo_history.id"), primary_key=True
    ),
    db.Column(
        "match_id",
        db.String,
        db.ForeignKey("match.match_id"),
        nullable=True,
    ),
)


team_match = db.Table(
    "team_match",
    db.Column("team_id", db.String, db.ForeignKey("team.team_id"), primary_key=True),
    db.Column("match_id", db.String, db.ForeignKey("match.match_id"), primary_key=True),
)
