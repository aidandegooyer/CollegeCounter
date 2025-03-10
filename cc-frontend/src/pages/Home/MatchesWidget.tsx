import { useQueryClient } from "@tanstack/react-query";
import React, { useEffect, useState } from "react";
import { Button, Card, Col, Container, Row } from "react-bootstrap";
import { Link } from "react-router-dom";
import { Team, Match } from "../../types";
import { format } from "date-fns";
import logo from "../../assets/0.5x/C Logo@0.5x.png";
const apiBaseUrl =
  import.meta.env.VITE_API_BASE_URL || "https://api.collegecounter.org";

const fetchTeam = async (teamId: string): Promise<Team> => {
  const response = await fetch(`${apiBaseUrl}/team/${teamId}`);
  return response.json();
};

const MatchCard = ({ match }: { match: Match }) => (
  <Card key={match.match_id} style={{ marginBottom: "10px" }}>
    <Card.Body>
      <Row>
        <Col>
          <Row>
            <div className="d-flex align-items-center">
              <img
                src={
                  match.teams?.team1?.avatar ? match.teams.team1.avatar : logo
                }
                style={{ height: "30px", width: "30px", marginRight: "10px" }}
              />
              <Card.Title
                style={{
                  whiteSpace: "nowrap", // Ensures all items stay inline
                  overflow: "hidden", // Prevents content from overflowing
                }}
              >
                <Link
                  to={`/team?id=${match.teams?.team1?.team_id}`}
                  style={{
                    overflow: "hidden",
                    textOverflow: "ellipsis",
                    whiteSpace: "nowrap",
                    display: "inline",
                    marginLeft: "5px",
                    color: "var(--bs-body-color)",
                  }}
                >
                  {match.teams?.team1?.name}
                </Link>
              </Card.Title>
            </div>
          </Row>
          <Row>
            <div className="d-flex align-items-center">
              <img
                src={
                  match.teams?.team2?.avatar ? match.teams.team2.avatar : logo
                }
                style={{ height: "30px", width: "30px", marginRight: "10px" }}
              />
              <Card.Title
                style={{
                  whiteSpace: "nowrap", // Ensures all items stay inline
                  overflow: "hidden", // Prevents content from overflowing
                }}
              >
                <Link
                  to={`/team?id=${match.teams?.team2?.team_id}`}
                  style={{
                    overflow: "hidden",
                    textOverflow: "ellipsis",
                    whiteSpace: "nowrap",
                    display: "inline",
                    marginLeft: "5px",
                    color: "var(--bs-body-color)",
                  }}
                >
                  {match.teams?.team2?.name}
                </Link>
              </Card.Title>
            </div>
          </Row>
        </Col>
      </Row>
      <Row className="align-items-center mt-2">
        <Col>
          <Card.Text>
            {format(new Date(match.scheduled_time * 1000), "MMMM do, h:mm aaa")}
          </Card.Text>
        </Col>
        <Col xs={3}>
          <div
            style={{
              display: "flex",
              justifyContent: "center",
              alignItems: "center",
              height: "100%",
            }}
          >
            <Button variant="primary">View</Button>
          </div>
        </Col>
      </Row>
    </Card.Body>
  </Card>
);

const MatchesWidget: React.FC = () => {
  const [matches, setMatches] = useState<Match[]>([]);
  const queryClient = useQueryClient();

  const fetchMatches = async () => {
    const response = await fetch(`${apiBaseUrl}/upcoming/4`);
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

  useEffect(() => {
    const fetchAndSetMatches = async () => {
      const matches = await fetchMatches();
      setMatches(matches);
    };
    fetchAndSetMatches();
  }, []);

  return (
    <>
      <Container
        style={{
          position: "sticky",
          top: "60px",
          zIndex: 1000,
        }}
      >
        <Row>
          <Col
            style={{
              borderRight: "1px solid #dee2e6",
              borderLeft: "1px dotted #dee2e6",
            }}
          >
            <h3>Upcoming Matches</h3>
            {matches.map((match) => (
              <MatchCard match={match} key={match.match_id} />
            ))}
            <div
              style={{
                display: "flex",
                justifyContent: "center",
                marginTop: "10px",
              }}
            >
              <Button variant="info">
                <Link
                  to="/matches"
                  style={{ color: "white", textDecoration: "none" }}
                >
                  View More
                  <i
                    className="bi bi-arrow-right"
                    style={{ marginLeft: "5px" }}
                  ></i>
                </Link>
              </Button>
            </div>
          </Col>
        </Row>
      </Container>
    </>
  );
};

export default MatchesWidget;
