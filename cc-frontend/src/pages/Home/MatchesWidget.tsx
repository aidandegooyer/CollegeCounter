import { useQueryClient } from "@tanstack/react-query";
import React, { useEffect, useState } from "react";
import { Button, Card, Col, Container, Row, Image } from "react-bootstrap";
import { Link } from "react-router-dom";
import { Team, Match } from "../../types";
import { format, set } from "date-fns";
import logo from "../../assets/1x/C Logo.png";

const fetchTeam = async (teamId: string): Promise<Team> => {
  const response = await fetch(`http://localhost:8889/team/${teamId}`);
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
                src={match.teams?.team1?.avatar}
                style={{ height: "30px", width: "30px", marginRight: "10px" }}
              />
              <Card.Title>
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
                src={match.teams?.team2?.avatar}
                style={{ height: "30px", width: "30px", marginRight: "10px" }}
              />
              <Card.Title>
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
    const response = await fetch("http://localhost:8889/upcoming/4");
    const matches: Match[] = await response.json();

    const matchesWithTeams = await Promise.all(
      matches.map(async (match) => {
        const team1 = await queryClient.fetchQuery({
          queryKey: ["team", match.team1_id],
          queryFn: () => fetchTeam(match.team1_id),
        });
        const team2 = await queryClient.fetchQuery({
          queryKey: ["team", match.team2_id],
          queryFn: () => fetchTeam(match.team2_id),
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
      <Image
        src={logo}
        style={{ width: "100%", height: "auto", marginBottom: "1rem" }}
      />
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
            <h3 style={{ fontSize: "1.5rem" }}>Upcoming Matches</h3>
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
