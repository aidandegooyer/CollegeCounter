import {
  Button,
  Card,
  Image,
  Container,
  Badge,
  Col,
  Row,
} from "react-bootstrap";
import { useLocation } from "react-router-dom";
import MatchCard from "../Matches/MatchCard";
import ResultCard from "../Results/ResultCard";
import { useEffect, useState } from "react";
import { Team, Match, Player } from "../../types";
import { useQueryClient } from "@tanstack/react-query";
import "./TeamPageBackground.css";
const apiBaseUrl =
  import.meta.env.VITE_API_BASE_URL || "https://api.collegecounter.org";

interface PlayerCardProps {
  player: Player;
  leader: boolean;
}

const fetchTeam = async (teamId: string): Promise<Team> => {
  const response = await fetch(`${apiBaseUrl}/team/${teamId}`);
  return response.json();
};

const PlayerCard: React.FC<PlayerCardProps> = ({ player, leader }) => {
  const handlePlayerClick = () => {
    // open new tab with player profile
    window.open(`https://www.faceit.com/en/players/${player.nickname}`);
  };

  const getLevelColor = (level: number) => {
    if (level < 3) {
      return "secondary";
    } else if (level < 6) {
      return "success";
    } else if (level < 8) {
      return "warning";
    } else if (level < 10) {
      return "primary";
    } else {
      return "danger";
    }
  };

  return (
    <>
      <img src={player.avatar} style={{ width: "200px" }} />
      <Card style={{ width: "200px" }}>
        <Card.Title
          className="text-center"
          style={{ fontSize: "1.5rem", marginTop: "1rem" }}
        >
          {leader ? (
            <i
              className="bi bi-star"
              style={{ fontSize: "1rem", color: "gold", marginRight: "0.5rem" }}
            />
          ) : (
            ""
          )}
          {player.nickname}
        </Card.Title>
        <div className="d-flex justify-content-center">
          <Badge
            bg={getLevelColor(player.skill_level)}
            style={{ width: "70px" }}
          >
            Level: {player.skill_level}
          </Badge>
        </div>
        <Button
          className="d-none d-md-block"
          variant="primary"
          style={{ margin: "1rem" }}
          onClick={handlePlayerClick}
        >
          View Profile
        </Button>
      </Card>
    </>
  );
};

const TeamPage = () => {
  const location = useLocation();
  const searchParams = new URLSearchParams(location.search);
  const id = searchParams.get("id");

  const queryClient = useQueryClient();

  // get team info from http://0.0.0.0:8889/team/a606b5d2-08e3-46fa-8f24-1d5bc397cc1b
  const [team, setTeam] = useState<Team | null>(null);
  const [upcomingMatches, setUpcomingMatches] = useState<any[]>([]);
  const [pastMatches, setPastMatches] = useState<any[]>([]);

  const fetchTeamInfo = async () => {
    try {
      const response = await fetch(`${apiBaseUrl}/team/${id}`);
      const data: Team = await response.json();
      setTeam(data);
    } catch (error) {
      console.error("Error fetching team info:", error);
    }
  };

  const fetchMatches = async () => {
    const response = await fetch(`${apiBaseUrl}/team/${id}/matches`);
    const matches: Match[] = await response.json();

    const matchesWithTeams = await Promise.all(
      matches.map(async (match) => {
        const team1 = await queryClient.fetchQuery({
          queryKey: ["team", match.team1_id],
          queryFn: () => fetchTeam(match.team1_id),
          staleTime: 1000 * 60 * 10,
        });
        const team2 = await queryClient.fetchQuery({
          queryKey: ["team", match.team2_id],
          queryFn: () => fetchTeam(match.team2_id),
          staleTime: 1000 * 60 * 10,
        });
        return { ...match, teams: { team1, team2 } };
      })
    );
    return matchesWithTeams;
  };
  const fetchTeamPlayers = async () => {
    try {
      const response = await fetch(`${apiBaseUrl}/team/${id}/players`);
      const players: Player[] = await response.json();
      setTeam((prevTeam) => {
        if (prevTeam) {
          return { ...prevTeam, roster: players };
        }
        return prevTeam;
      });
    } catch (error) {
      console.error("Error fetching team players:", error);
    }
  };

  useEffect(() => {
    if (id) {
      fetchTeamInfo();
      const matches = fetchMatches();
      matches.then((allMatches) => {
        const upcoming = allMatches.filter(
          (match) => match.status === "SCHEDULED"
        );
        const past = allMatches.filter((match) => match.status === "FINISHED");

        setUpcomingMatches(upcoming);
        setPastMatches(past);
      });
      fetchTeamPlayers();
    }
  }, [id]);

  useEffect(() => {
    document.title = team ? `CC - ${team.name}` : "CC - Team";
  }, [team?.name]);

  if (!team) {
    return <div>Team not found</div>;
  }

  return (
    <>
      <div
        className="background"
        style={{
          backgroundImage: `url('${apiBaseUrl}/static/bg/${team.team_id}.png')`,
        }}
      />
      <Container style={{ marginTop: "0.5rem", padding: "0 1rem" }}>
        <h1 className="text-center">Team Details</h1>
        <div className="d-flex justify-content-center align-items-center">
          <Image
            src={team.avatar}
            alt={team.name}
            style={{ height: "5rem", marginRight: "1rem" }}
            fluid
          />
          <h1 className="text-center" style={{ fontSize: "5rem" }}>
            {team.name}
          </h1>
        </div>

        <Container style={{ marginTop: "1rem" }}>
          <div className="d-flex justify-content-center">
            <div className="d-flex flex-wrap justify-content-center">
              {team.roster ? (
                team.roster
                  .sort((a, b) => {
                    if (team.leader === a.player_id) return -1;
                    if (team.leader === b.player_id) return 1;
                    return a.nickname.localeCompare(b.nickname);
                  })
                  .map((player) => (
                    <div
                      key={player.player_id}
                      className="p-2"
                      style={{
                        flex: "1 0 200px",
                        maxWidth: "200px",
                        margin: "0 1rem",
                      }}
                    >
                      <PlayerCard
                        player={player}
                        leader={team.leader === player.player_id}
                      />
                    </div>
                  ))
              ) : (
                <p>No players found</p>
              )}
            </div>
          </div>
        </Container>

        <Container style={{ marginTop: "4rem" }}>
          <Row>
            <Col md={12} lg={6}>
              <h1 className="text-center">Upcoming Matches</h1>
              {upcomingMatches.length > 0 ? (
                upcomingMatches
                  .sort(
                    (a: Match, b: Match) =>
                      new Date(a.scheduled_time).getTime() -
                      new Date(b.scheduled_time).getTime()
                  )
                  .map((match, index) => (
                    <MatchCard
                      key={match.match_id}
                      match={match}
                      today={index === 0}
                      thisweek={index !== 0}
                    />
                  ))
              ) : (
                <p className="text-center">No upcoming matches</p>
              )}
            </Col>
            <Col md={12} lg={6}>
              <h1 className="text-center">Past Match Results</h1>
              {pastMatches.length > 0 ? (
                pastMatches
                  .sort(
                    (a: Match, b: Match) =>
                      new Date(b.scheduled_time).getTime() -
                      new Date(a.scheduled_time).getTime()
                  )
                  .map((match) => (
                    <ResultCard key={match.match_id} match={match} />
                  ))
              ) : (
                <p className="text-center">No past matches</p>
              )}
            </Col>
          </Row>
        </Container>
      </Container>
    </>
  );
};

export default TeamPage;
