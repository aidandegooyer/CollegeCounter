import { format } from "date-fns";
import { useState, useEffect } from "react";
import { Card, Row, Col, Button, Image, Badge, Alert } from "react-bootstrap";
import { Link } from "react-router-dom";
import { Match, Team } from "../../types";
import React from "react";

interface ResultCardProps {
  match: Match;
}

const ResultCard: React.FC<ResultCardProps> = ({ match }) => {
  const [winner, setWinner] = useState<Team | null>(null);
  const [loser, setLoser] = useState<Team | null>(null);
  const [winnerFaction, setWinnerFaction] = useState<string>("");

  function openMatchPage(match: Match) {
    const url = match.match_url.replace("{lang}", "en");
    window.open(url, "_blank")?.focus();
  }

  if (match.teams === undefined || match.results_winner === undefined) {
    return <Alert variant="danger">Error: Match data not found</Alert>;
  }

  function getMatchResults(match: Match) {
    if (match.teams === undefined) {
      return;
    }
    if (match.results_winner) {
      setWinnerFaction(match.results_winner);
      setWinner(
        match.results_winner === "faction1"
          ? match.teams.team1
          : match.teams.team2
      );
      setLoser(
        match.results_winner === "faction1"
          ? match.teams.team2
          : match.teams.team1
      );
    }
  }

  useEffect(() => {
    getMatchResults(match);
  }, []);
  if (winner && loser) {
    return (
      <Card style={{ marginBottom: "1rem" }}>
        <Card.Body>
          <Row className="text-center">
            <Col md={2}>
              <Image
                src={match.teams.team1.avatar}
                style={{ maxWidth: "100px", width: "100%" }}
              ></Image>
            </Col>
            <Col
              md={4}
              style={{ color: winnerFaction === "faction1" ? "white" : "grey" }}
            >
              <Row className="justify-content-center">
                <h4>
                  <Link
                    style={{
                      overflow: "hidden",
                      textOverflow: "ellipsis",
                      whiteSpace: "nowrap",
                      display: "block",
                      textDecoration: "none",
                      color:
                        winnerFaction === "faction1"
                          ? "var(--bs-body-color)"
                          : "grey",
                    }}
                    to={`/team?id=${match.teams.team1.team_id}`}
                  >
                    {match.teams.team1.name}
                  </Link>
                </h4>
              </Row>
              <Row className="justify-content-center">
                <h1>{match.results_score_team1}</h1>
              </Row>
            </Col>
            <Col
              md={4}
              style={{ color: winnerFaction === "faction2" ? "white" : "grey" }}
            >
              <Row className="justify-content-center">
                <h4>
                  <Link
                    style={{
                      textDecoration: "none",
                      color:
                        winnerFaction === "faction2"
                          ? "var(--bs-body-color)"
                          : "grey",
                      overflow: "hidden",
                      textOverflow: "ellipsis",
                      whiteSpace: "nowrap",
                      display: "block",
                    }}
                    to={`/team?id=${match.teams.team2.team_id}`}
                  >
                    {match.teams.team2.name}
                  </Link>
                </h4>
              </Row>
              <Row className="justify-content-center">
                <h1>{match.results_score_team2}</h1>
              </Row>
            </Col>
            <Col md={2}>
              <Image
                src={match.teams.team2.avatar}
                style={{ maxWidth: "100px", width: "100%" }}
                fluid
              ></Image>
            </Col>
          </Row>
        </Card.Body>
        <Card.Footer>
          <Row className="align-items-center text-center">
            <Col className="text-center">
              {match.scheduled_time
                ? format(new Date(match.scheduled_time * 1000), "MMM do, yyyy")
                : "Date not available"}
              <Badge bg="secondary" style={{ marginLeft: "0.5rem" }}>
                {match.competition.toUpperCase()}
              </Badge>
            </Col>
            <Col>
              <Button
                variant="primary"
                onClick={() => openMatchPage(match)}
                style={{ width: "100%" }}
              >
                View Matchroom <i className="bi bi-arrow-right" />
              </Button>
            </Col>
          </Row>
        </Card.Footer>
      </Card>
    );
  }
};

export default ResultCard;
