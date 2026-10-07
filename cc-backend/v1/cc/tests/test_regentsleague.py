from unittest.mock import MagicMock, patch

from django.test import TestCase

from cc.models import Competition, Match, Participant, Season, Team
from cc.views import import_regentsleague_match_data, update_regentsleague_match


def regents_match(winner, status="Completed"):
    return {
        "id": 42,
        "status": status,
        "date": "2025-10-01T18:00:00Z",
        "team1": {"id": 1, "name": "Alpha"},
        "team2": {"id": 2, "name": "Bravo"},
        "score_team1": 1,
        "score_team2": 0,
        "winner": winner,
    }


class RegentsLeagueWinnerTests(TestCase):
    def setUp(self):
        self.season = Season.objects.create(
            name="S", start_date="2025-08-01", end_date="2026-05-01"
        )
        self.competition = Competition.objects.create(name="Regents")
        self.alpha = Team.objects.create(name="Alpha")
        self.bravo = Team.objects.create(name="Bravo")
        for team, rid in [(self.alpha, 1), (self.bravo, 2)]:
            Participant.objects.create(
                team=team,
                competition=self.competition,
                season=self.season,
                regentsleague_id=rid,
            )

    def test_import_completed_match_without_winner(self):
        for winner in (None, {}):
            Match.objects.all().delete()
            result = import_regentsleague_match_data(
                [regents_match(winner)], self.competition, self.season
            )
            self.assertEqual(len(result["imported"]), 1)
            match = Match.objects.get()
            self.assertEqual(match.status, "completed")
            self.assertIsNone(match.winner)

    def test_import_unknown_status_defaults_to_scheduled(self):
        import_regentsleague_match_data(
            [regents_match(None, status="Postponed")], self.competition, self.season
        )
        self.assertEqual(Match.objects.get().status, "scheduled")

    def _refresh(self, payload):
        match = Match.objects.create(
            team1=self.alpha,
            team2=self.bravo,
            date="2025-10-01T18:00:00Z",
            status="scheduled",
            regentsleague_id=42,
            competition=self.competition,
            season=self.season,
            platform="regentsleague",
        )
        response = MagicMock(status_code=200)
        response.json.return_value = payload
        with patch("cc.views.platform_sync.requests.get", return_value=response):
            update_regentsleague_match(match)
        match.refresh_from_db()
        return match

    def test_refresh_completed_match_without_winner(self):
        match = self._refresh(regents_match(None))
        self.assertEqual(match.status, "completed")
        self.assertIsNone(match.winner)

    def test_refresh_with_missing_participants_does_not_crash(self):
        Participant.objects.all().delete()
        match = self._refresh(regents_match({"id": 1}))
        self.assertIsNone(match.winner)
