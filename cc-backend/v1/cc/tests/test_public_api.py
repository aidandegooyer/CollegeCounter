from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status
import json

from cc.models import Team, Player, Match, Season, Event, EventMatch


class PublicAPITestCase(TestCase):
    def setUp(self):
        self.client = APIClient()

        # Create test data
        self.team1 = Team.objects.create(
            name="Test Team 1", school_name="Test School 1", elo=1200
        )

        self.team2 = Team.objects.create(
            name="Test Team 2", school_name="Test School 2", elo=1100
        )

        self.player1 = Player.objects.create(
            name="Test Player 1", skill_level=10, elo=1500, team=self.team1
        )

        self.player2 = Player.objects.create(
            name="Test Player 2", skill_level=8, elo=1400, team=self.team2
        )

        self.season = Season.objects.create(
            name="Test Season", start_date="2023-01-01", end_date="2023-12-31"
        )

        self.match = Match.objects.create(
            team1=self.team1,
            team2=self.team2,
            date="2023-06-15T14:00:00Z",
            status="completed",
            score_team1=16,
            score_team2=14,
            winner=self.team1,
        )

        self.event = Event.objects.create(
            name="Test Event",
            start_date="2023-06-01",
            end_date="2023-06-30",
            season=self.season,
        )

        self.event_match = EventMatch.objects.create(event=self.event, match=self.match)

    def test_public_teams_endpoint(self):
        """Test that the public teams endpoint returns all teams"""
        url = reverse("public_teams")
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = json.loads(response.content)
        self.assertEqual(content["count"], 2)

        # Test filtering by team name
        response = self.client.get(f"{url}?name=Team 1")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = json.loads(response.content)
        self.assertEqual(content["count"], 1)
        self.assertEqual(content["results"][0]["name"], "Test Team 1")

    def test_public_players_endpoint(self):
        """Test that the public players endpoint returns all players"""
        url = reverse("public_players")
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = json.loads(response.content)
        self.assertEqual(content["count"], 2)

        # Test filtering by team ID
        response = self.client.get(f"{url}?team_id={self.team1.id}")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = json.loads(response.content)
        self.assertEqual(content["count"], 1)
        self.assertEqual(content["results"][0]["name"], "Test Player 1")

    def test_public_matches_endpoint(self):
        """Test that the public matches endpoint returns all matches"""
        url = reverse("public_matches")
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = json.loads(response.content)
        self.assertEqual(content["count"], 1)

        # Test filtering by team ID
        response = self.client.get(f"{url}?team_id={self.team1.id}")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = json.loads(response.content)
        self.assertEqual(content["count"], 1)

        # Test filtering by status
        response = self.client.get(f"{url}?status=completed")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = json.loads(response.content)
        self.assertEqual(content["count"], 1)

        # Test filtering by season ID
        response = self.client.get(f"{url}?season_id={self.season.id}")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = json.loads(response.content)
        self.assertEqual(content["count"], 1)

    def test_public_seasons_endpoint(self):
        """Test that the public seasons endpoint returns all seasons"""
        url = reverse("public_seasons")
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = json.loads(response.content)
        self.assertEqual(content["count"], 1)

        # Test filtering by current season
        response = self.client.get(f"{url}?current=true")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = json.loads(response.content)
        self.assertEqual(content["count"], 1)  # Our test season is current
