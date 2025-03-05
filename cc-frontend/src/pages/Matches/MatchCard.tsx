import { format } from "date-fns";
import { useState, useEffect } from "react";
import {
  Card,
  Row,
  Col,
  Badge,
  Button,
  Alert,
  ProgressBar,
} from "react-bootstrap";
import { Link } from "react-router-dom";
import { Match } from "../../types";

interface MatchCardProps {
  match: Match;
  today?: boolean;
  thisweek?: boolean;
}

const MatchCard = ({ match, today, thisweek }: MatchCardProps) => {
  const [timeLeft, setTimeLeft] = useState<string>("");

  function openMatchPage(match: Match) {
    const url = match.match_url.replace("{lang}", "en");
    window.open(url, "_blank")?.focus();
  }

  useEffect(() => {
    if (today) {
      const interval = setInterval(() => {
        const now = new Date().getTime();
        const distance = match.scheduled_time * 1000 - now;

        if (distance < 0) {
          clearInterval(interval);
          setTimeLeft("Live");
        } else {
          const days = Math.floor(distance / (1000 * 60 * 60 * 24));
          const hours = Math.floor(
            (distance % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60)
          );
          const minutes = Math.floor(
            (distance % (1000 * 60 * 60)) / (1000 * 60)
          );
          const seconds = Math.floor((distance % (1000 * 60)) / 1000);
          setTimeLeft(`${days}d ${hours}h ${minutes}m ${seconds}s`);
        }
      }, 1000);

      return () => clearInterval(interval);
    }
  }, [today, match.scheduled_time]);

  if (match.teams === undefined) {
    return (
      <Alert variant="danger">
        This match is missing team information. Please contact an admin.
      </Alert>
    );
  }

  const expected_score =
    1 / (1 + 10 ** ((match.teams?.team2.elo - match.teams?.team1.elo) / 800));

  if (today) {
    return (
      <Card style={{ marginBottom: "1rem" }}>
        <Row style={{ padding: "1rem" }}>
          <Col>
            <Row style={{ marginBottom: "1rem" }}>
              <div style={{ display: "flex", alignItems: "center" }}>
                <img
                  src={match.teams.team1.avatar}
                  style={{ width: "50px", height: "50px" }}
                ></img>
                <h3 style={{ marginLeft: "10px", marginRight: "10px" }}>
                  <Link
                    style={{
                      color: "var(--bs-body-color)",
                      textDecoration: "none",
                    }}
                    to={`/team?id=${match.teams.team1.team_id}`}
                  >
                    {match.teams.team1.name}
                  </Link>
                </h3>
                <Badge bg="info">{match.teams.team1.elo.toPrecision(4)}</Badge>
              </div>
            </Row>
            <Row>
              <div style={{ display: "flex", alignItems: "center" }}>
                <img
                  src={match.teams.team2.avatar}
                  style={{ width: "50px", height: "50px" }}
                ></img>
                <h3 style={{ marginLeft: "10px", marginRight: "10px" }}>
                  <Link
                    style={{
                      color: "var(--bs-body-color)",
                      textDecoration: "none",
                    }}
                    to={`/team?id=${match.teams.team2.team_id}`}
                  >
                    {match.teams.team2.name}
                  </Link>
                </h3>
                <Badge bg="info">{match.teams.team2.elo.toPrecision(4)}</Badge>
              </div>
            </Row>
          </Col>
          <Col style={{ marginRight: "1rem" }} className="text-end">
            <Row className="justify-content-end">
              <h3>
                {format(new Date(match.scheduled_time * 1000), "h:mm aaa")}
              </h3>
            </Row>
            <Row className="justify-content-end">
              {timeLeft === "Live" ? (
                <Badge
                  bg="danger"
                  style={{ maxWidth: "120px", fontSize: "1.5rem" }}
                >
                  <i
                    className="bi bi-broadcast"
                    style={{ marginRight: "10px" }}
                  />
                  Live
                </Badge>
              ) : (
                <h3>{timeLeft}</h3>
              )}
            </Row>
            <Row className="justify-content-end">
              <Badge
                className="mt-2"
                bg="secondary"
                style={{ maxWidth: "75px", fontSize: "1rem" }}
              >
                {match.competition.toUpperCase()}
              </Badge>
            </Row>
          </Col>
        </Row>
        <h6
          style={{
            margin: "1rem",
            marginTop: "0",
            marginBottom: "0",
          }}
        >
          Win Probability:
        </h6>
        <ProgressBar
          style={{
            margin: "1rem",
            marginTop: "0.25rem",
          }}
        >
          <ProgressBar
            now={Math.round(expected_score * 100)}
            label={
              match.teams.team1.name +
              " " +
              Math.round(expected_score * 100) +
              "%"
            }
            variant="info"
          />
          <ProgressBar
            now={Math.round((1 - expected_score) * 100)}
            label={
              match.teams.team2.name +
              " " +
              Math.round((1 - expected_score) * 100) +
              "%"
            }
            variant="primary"
          />
        </ProgressBar>
        <Button
          variant="primary"
          style={{
            margin: "1rem",
            marginTop: "0",
          }}
          onClick={() => openMatchPage(match)}
        >
          Details <i className="bi bi-arrow-right" />
        </Button>
      </Card>
    );
  }

  if (thisweek) {
    return (
      <Card style={{ marginBottom: "1rem" }}>
        <Row style={{ padding: "1rem" }}>
          <Col md={8}>
            <Row style={{ marginBottom: "1rem" }}>
              <div style={{ display: "flex", alignItems: "center" }}>
                <img
                  src={match.teams.team1.avatar}
                  style={{ width: "50px", height: "50px" }}
                ></img>
                <h4 style={{ marginLeft: "10px", marginRight: "10px" }}>
                  <Link
                    style={{
                      color: "var(--bs-body-color)",
                      textDecoration: "none",
                    }}
                    to={`/team?id=${match.teams.team1.team_id}`}
                  >
                    {match.teams.team1.name}
                  </Link>
                </h4>
                <Badge bg="info">{match.teams.team1.elo.toPrecision(4)}</Badge>
              </div>
            </Row>
            <Row>
              <div style={{ display: "flex", alignItems: "center" }}>
                <img
                  src={match.teams.team2.avatar}
                  style={{ width: "50px", height: "50px" }}
                ></img>
                <h4 style={{ marginLeft: "10px", marginRight: "10px" }}>
                  <Link
                    style={{
                      color: "var(--bs-body-color)",
                      textDecoration: "none",
                    }}
                    to={`/team?id=${match.teams.team2.team_id}`}
                  >
                    {match.teams.team2.name}
                  </Link>
                </h4>
                <Badge bg="info">{match.teams.team2.elo.toPrecision(4)}</Badge>
              </div>
            </Row>
          </Col>
          <Col style={{ marginRight: "1rem" }}>
            <Row className="justify-content-end">
              {format(
                new Date(match.scheduled_time * 1000),
                "MMM do, h:mm aaa"
              )}
            </Row>
            <Row className="justify-content-end mt-3">
              <Badge bg="secondary" style={{ maxWidth: "50px" }}>
                {match.competition.toUpperCase()}
              </Badge>
            </Row>
            <Row className="justify-content-end mt-3">
              <Button
                variant="primary"
                style={{
                  maxWidth: "100px",
                  height: "40px",
                }}
                onClick={() => openMatchPage(match)}
              >
                Details <i className="bi bi-arrow-right" />
              </Button>
            </Row>
          </Col>
        </Row>
      </Card>
    );
  }

  return (
    <Card style={{ marginBottom: "1rem", maxWidth: "400px" }}>
      <Row>
        <Col md={8}>
          <Row>
            <div style={{ display: "flex", alignItems: "center" }}>
              <img
                src={match.teams.team1.avatar}
                style={{ width: "30px", height: "30px" }}
              ></img>
              <h6 style={{ marginLeft: "10px", marginRight: "10px" }}>
                {match.teams.team1.name}
              </h6>
              <Badge bg="info">{match.teams.team1.elo.toPrecision(4)}</Badge>
            </div>
          </Row>
          <Row>
            <div style={{ display: "flex", alignItems: "center" }}>
              <img
                src={match.teams.team2.avatar}
                style={{ width: "30px", height: "30px" }}
              ></img>
              <h6 style={{ marginLeft: "10px", marginRight: "10px" }}>
                {match.teams.team2.name}
              </h6>
              <Badge bg="info">{match.teams.team2.elo.toPrecision(4)}</Badge>
            </div>
          </Row>
        </Col>
        <Col md={4} className="text-end">
          <Row className="justify-content-end" style={{ marginRight: "1rem" }}>
            {format(new Date(match.scheduled_time * 1000), "MMM do")}
          </Row>
          <Row className="justify-content-end" style={{ marginRight: "1rem" }}>
            {format(new Date(match.scheduled_time * 1000), "h:mm aaa")}
          </Row>
        </Col>
      </Row>
    </Card>
  );
};

export default MatchCard;
