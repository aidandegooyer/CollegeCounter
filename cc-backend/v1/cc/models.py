import uuid
from django.core.validators import MinValueValidator
from django.db import models
from django.core.exceptions import ValidationError


class Team(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100)
    picture = models.URLField(blank=True, null=True)
    school_name = models.CharField(max_length=100, blank=True, null=True)
    elo = models.IntegerField(default=1000, validators=[MinValueValidator(0)])
    captain = models.ForeignKey(
        "Player",
        on_delete=models.SET_NULL,
        related_name="captain_of",
        null=True,
        blank=True,
        help_text="Must be one of this team's roster",
    )

    def clean(self):
        # optional: raise a ValidationError before hitting the DB constraint
        if self.captain and self.captain.team_id != self.id:
            raise ValidationError({"captain": "Captain must be a member of this team."})

    def __str__(self):
        return self.name


class Player(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100)
    picture = models.URLField(blank=True, null=True)
    skill_level = models.IntegerField(default=0, validators=[MinValueValidator(0)])
    steam_id = models.CharField(
        max_length=100, unique=True, blank=True, null=True, db_index=True
    )
    faceit_id = models.CharField(
        max_length=100, unique=True, blank=True, null=True, db_index=True
    )
    elo = models.IntegerField(default=1000, validators=[MinValueValidator(0)])
    team = models.ForeignKey(
        Team, on_delete=models.CASCADE, related_name="roster", blank=True, null=True
    )
    benched = models.BooleanField(default=False)
    visible = models.BooleanField(default=True)

    def __str__(self):
        return self.name


class Match(models.Model):
    """
    Model representing a match.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    team1 = models.ForeignKey(
        Team, on_delete=models.CASCADE, related_name="matches_as_team1"
    )
    team2 = models.ForeignKey(
        Team, on_delete=models.CASCADE, related_name="matches_as_team2"
    )
    date = models.DateTimeField()
    status = models.CharField(
        max_length=20,
        choices=[
            ("scheduled", "Scheduled"),
            ("in_progress", "In Progress"),
            ("completed", "Completed"),
            ("cancelled", "Cancelled"),
        ],
        default="scheduled",
    )
    season = models.ForeignKey(
        "Season",
        on_delete=models.CASCADE,
        related_name="matches",
        blank=True,
        null=True,
    )
    competition = models.ForeignKey(
        "Competition",
        on_delete=models.CASCADE,
        related_name="matches",
        blank=True,
        null=True,
    )
    url = models.URLField(blank=True, null=True, help_text="Link to match details")
    winner = models.ForeignKey(
        Team,
        on_delete=models.SET_NULL,
        related_name="matches_won",
        null=True,
        blank=True,
        help_text="Team that won the match, if applicable",
    )
    score_team1 = models.IntegerField(default=0)
    score_team2 = models.IntegerField(default=0)
    platform = models.CharField(
        max_length=20,
        default="other",
    )

    def __str__(self):
        return (
            f"{self.team1} vs {self.team2} on {self.date.strftime('%Y-%m-%d %H:%M:%S')}"
        )


class Season(models.Model):
    """
    Model representing a season.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100)
    start_date = models.DateTimeField()
    end_date = models.DateTimeField()

    def __str__(self):
        return self.name


class Participant(models.Model):
    """
    Model representing a participant in a competition.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    team = models.ForeignKey(
        Team,
        on_delete=models.CASCADE,
        related_name="participants",
        blank=True,
        null=True,
    )
    competition = models.ForeignKey(
        "Competition",
        on_delete=models.CASCADE,
        related_name="participants",
        blank=True,
        null=True,
    )
    faceit_id = models.CharField(
        max_length=100, unique=True, blank=True, null=True, db_index=True
    )
    playfly_id = models.CharField(
        max_length=100, unique=True, blank=True, null=True, db_index=True
    )
    playfly_participant_id = models.CharField(
        max_length=100, unique=True, blank=True, null=True, db_index=True
    )
    season = models.ForeignKey(
        Season,
        on_delete=models.CASCADE,
        related_name="participants",
        blank=True,
        null=True,
    )

    def __str__(self):
        return f"{self.team.name if self.team else 'No Team'} - {self.competition.name if self.competition else 'No Competition'}"


class Ranking(models.Model):
    """
    Model representing a ranking.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    date = models.DateTimeField(auto_now_add=True)
    season = models.ForeignKey(
        Season,
        on_delete=models.CASCADE,
        related_name="rankings",
        blank=True,
        null=True,
    )

    def __str__(self):
        return f"Ranking on {self.date.strftime('%Y-%m-%d %H:%M:%S')}"


class RankingItem(models.Model):
    """
    Model representing an item in a ranking.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    ranking = models.ForeignKey(
        Ranking, on_delete=models.CASCADE, related_name="ranking_items"
    )
    team = models.ForeignKey(
        Team, on_delete=models.CASCADE, related_name="ranking_items"
    )
    rank = models.IntegerField(validators=[MinValueValidator(1)])
    elo = models.IntegerField(default=1000, validators=[MinValueValidator(0)])

    def __str__(self):
        return f"{self.team.name} - Rank {self.rank} - Elo {self.elo}"


class Event(models.Model):
    """
    Model representing an event.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100)
    start_date = models.DateTimeField()
    end_date = models.DateTimeField()
    description = models.TextField(blank=True, null=True)
    winner = models.ForeignKey(
        Team,
        on_delete=models.SET_NULL,
        related_name="events_won",
        null=True,
        blank=True,
        help_text="Team that won the event, if applicable",
    )
    picture = models.URLField(blank=True, null=True, help_text="Event picture URL")
    season = models.ForeignKey(
        Season,
        on_delete=models.CASCADE,
        related_name="events",
        blank=True,
        null=True,
    )

    def __str__(self):
        return self.name


class EventMatch(models.Model):
    """
    Model representing a match in an event.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    match = models.ForeignKey(
        Match, on_delete=models.CASCADE, related_name="event_matches"
    )
    round = models.IntegerField(
        default=1,
        validators=[MinValueValidator(1)],
        help_text="Round number in the event",
    )
    num_in_bracket = models.IntegerField(
        default=1,
        validators=[MinValueValidator(1)],
        help_text="Match number in the bracket",
    )
    event = models.ForeignKey(
        Event, on_delete=models.CASCADE, related_name="event_matches"
    )
    is_bye = models.BooleanField(
        default=False, help_text="Indicates if this match is a bye round"
    )

    def __str__(self):
        return f"EVENTMATCH: {self.match.team1} vs {self.match.team2} on {self.match.date.strftime('%Y-%m-%d %H:%M:%S')}"


class Competition(models.Model):
    """
    Model representing a competition.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name
