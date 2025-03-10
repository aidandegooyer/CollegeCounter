import {
  Image,
  Container,
  Col,
  Row,
  Spinner,
  Alert,
  Badge,
} from "react-bootstrap";
import { Link, useLocation } from "react-router-dom";
import MatchCard from "../Matches/MatchCard";
import ResultCard from "../Results/ResultCard";
import { useEffect } from "react";
import { Team, Match, Player } from "../../types";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import errorImage from "../../assets/error-profile-pic.png";
import PlayerCard from "./PlayerCard";
import "./TeamPageBackground.css";
const apiBaseUrl =
  import.meta.env.VITE_API_BASE_URL || "https://api.collegecounter.org";

const fetchTeam = async (teamId: string): Promise<Team> => {
  const response = await fetch(`${apiBaseUrl}/team/${teamId}`);
  return response.json();
};

const fetchPlayers = async (teamId: string): Promise<Player[]> => {
  const response = await fetch(`${apiBaseUrl}/team/${teamId}/players`);
  return response.json();
};

const fetchTeamMatches = async (
  teamId: string,
  queryClient: any
): Promise<Match[]> => {
  const response = await fetch(`${apiBaseUrl}/team/${teamId}/matches`);
  if (!response.ok) {
    throw new Error("Error fetching team matches");
  }
  const matches: Match[] = await response.json();

  // For each match, fetch the teams for both sides
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

const fetchRank = async (teamId: string): Promise<number> => {
  const response = await fetch(`${apiBaseUrl}/team/${teamId}/rank`);
  const data = await response.json();
  return data.rank;
};

const TeamPage = () => {
  const location = useLocation();
  const searchParams = new URLSearchParams(location.search);
  const teamId = searchParams.get("id");

  const queryClient = useQueryClient();

  // Fetch team information
  const {
    data: team,
    isLoading: teamLoading,
    error: teamErrorObj,
    isError: teamError,
  } = useQuery<Team>({
    queryKey: ["team", teamId],
    queryFn: () => fetchTeam(teamId!),
    enabled: !!teamId,
    staleTime: 1000 * 60 * 10,
  });

  // Fetch team rank
  const {
    data: rank,
    isLoading: rankLoading,
    error: rankErrorObj,
    isError: rankError,
  } = useQuery<number>({
    queryKey: ["team", teamId, "rank"],
    queryFn: () => fetchRank(teamId!),
    enabled: !!teamId,
    staleTime: 1000 * 60 * 10,
  });

  // Fetch team players
  const {
    data: players,
    isLoading: playersLoading,
    error: playersErrorObj,
    isError: playersError,
  } = useQuery<Player[]>({
    queryKey: ["team", teamId, "players"],
    queryFn: () => fetchPlayers(teamId!),
    enabled: !!teamId,
    staleTime: 1000 * 60 * 10,
  });

  // Fetch team matches (and enrich each with team info)
  const {
    data: matches,
    isLoading: matchesLoading,
    error: matchesErrorObj,
    isError: matchesError,
  } = useQuery<Match[]>({
    queryKey: ["team", teamId, "matches"],
    queryFn: () => fetchTeamMatches(teamId!, queryClient),
    enabled: !!teamId,
  });

  // Update document title once team data is available
  useEffect(() => {
    document.title = team ? `CC - ${team.name}` : "CC - Team";
  }, [team]);

  // Handle loading and error states for team info
  if (teamLoading || matchesLoading || playersLoading || rankLoading)
    return (
      <div
        style={{
          display: "flex",
          justifyContent: "center",
          alignItems: "center",
          height: "100vh",
        }}
      >
        <Spinner animation="border" />
      </div>
    );
  if (teamError || matchesError || playersError || rankError)
    return (
      <div
        style={{
          maxWidth: "800px",
          display: "flex",
          justifyContent: "center",
          alignItems: "center",
        }}
      >
        <Alert variant="danger">
          {" "}
          <strong>Error: </strong>
          Error loading team info:{" "}
          {teamErrorObj?.message ||
            matchesErrorObj?.message ||
            playersErrorObj?.message ||
            rankErrorObj?.message ||
            "Unknown Error"}
        </Alert>{" "}
      </div>
    );

  // Filter matches into upcoming and past matches
  const upcomingMatches =
    matches?.filter((match) => match.status === "SCHEDULED") || [];
  const pastMatches =
    matches?.filter((match) => match.status === "FINISHED") || [];

  return (
    <>
      <div
        className="background"
        style={{
          backgroundImage: team
            ? `url('${apiBaseUrl}/static/bg/${team.team_id}.png')`
            : "none",
        }}
      />
      <Container style={{ marginTop: "0.5rem", padding: "0 1rem" }}>
        <h1 className="text-center">Team Details</h1>
        <div className="d-flex justify-content-center align-items-center">
          <Image
            src={team?.avatar}
            alt={team?.name}
            style={{ height: "5rem", marginRight: "1rem" }}
            onError={(e) => {
              e.currentTarget.onerror = null;
              e.currentTarget.src = errorImage;
            }}
            fluid
          />
          <h1 className="text-center" style={{ fontSize: "5rem" }}>
            {team?.name}
          </h1>
        </div>
        <div className="d-flex justify-content-center align-items-center mt-2">
          {team?.faceit_id ? (
            <Badge bg="secondary" className="mx-1">
              NECC
            </Badge>
          ) : null}
          {team?.playfly_id ? (
            <Badge bg="info" className="mx-1">
              PlayFly
            </Badge>
          ) : null}
        </div>
        <div className="d-flex justify-content-center align-items-center mt-2">
          <h3>
            Rank: <Link to="/rankings">#{rank}</Link>
          </h3>
        </div>

        <Container style={{ marginTop: "1rem" }}>
          <div className="d-flex justify-content-center">
            <div className="d-flex flex-wrap justify-content-center">
              {players ? (
                players
                  .sort((a, b) => {
                    if (team?.leader === a.player_id) return -1;
                    if (team?.leader === b.player_id) return 1;
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
                        leader={team?.leader === player.player_id}
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
