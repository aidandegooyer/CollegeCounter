import { format } from "date-fns";
import { useState, useEffect } from "react";
import { Card, Row, Col, Badge, Button, ProgressBar } from "react-bootstrap";
import { Link } from "react-router-dom";
import { Match, Team } from "../../types";
import errorImage from "../../assets/error-profile-pic.png";
import logo from "../../assets/0.5x/C Logo@0.5x.png";

import { useQuery } from "@tanstack/react-query";
const apiBaseUrl =
  import.meta.env.VITE_API_BASE_URL || "https://api.collegecounter.org";

const fetchTeam = async (teamid: string): Promise<Team> => {
  const response = await fetch(`${apiBaseUrl}/team/${teamid}`);
  if (!response.ok) {
    throw new Error("Error fetching team");
  }
  return response.json();
};

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
          const timeComponents = [
            days > 0 ? `${days}d` : "",
            hours > 0 ? `${hours}h` : "",
            minutes > 0 ? `${minutes}m` : "",
            seconds > 0 ? `${seconds}s` : "",
          ]
            .filter(Boolean)
            .join(" ");
          setTimeLeft(timeComponents);
        }
      }, 1000);

      return () => clearInterval(interval);
    }
  }, [today, match.scheduled_time]);

  const {
    data: team1Data,
    isPending: team1Pending,
    isError: team1Error,
    error: team1ErrorObj,
  } = useQuery({
    queryKey: ["team", match.team1_id],
    queryFn: () => fetchTeam(match.team1_id),
    staleTime: 1000 * 60 * 10,
    enabled: !match.teams, // only run if teams are not already provided
  });

  const {
    data: team2Data,
    isPending: team2Pending,
    isError: team2Error,
    error: team2ErrorObj,
  } = useQuery({
    queryKey: ["team", match.team2_id],
    queryFn: () => fetchTeam(match.team2_id),
    staleTime: 1000 * 60 * 10,
    enabled: !match.teams,
  });

  if (!match.teams && (team1Pending || team2Pending)) {
    return <p>Loading teams...</p>;
  }

  if (!match.teams && (team1Error || team2Error)) {
    return (
      <p>
        Error:{" "}
        {team1ErrorObj?.message || team2ErrorObj?.message || "Unknown error"}
      </p>
    );
  }

  // Use provided team data if available, otherwise use fetched data
  const team1: Team = match.teams ? match.teams.team1 : (team1Data as Team);
  const team2: Team = match.teams ? match.teams.team2 : (team2Data as Team);

  let expected_score: number | undefined;
  if (team1 && team2) {
    expected_score = 1 / (1 + 10 ** ((team2.elo - team1.elo) / 800));
  }

  if (today) {
    return (
      <Card style={{ marginBottom: "1rem" }}>
        <Row style={{ padding: "1rem" }}>
          <Col>
            <Row style={{ marginBottom: "1rem" }}>
              <div style={{ display: "flex", alignItems: "center" }}>
                <img
                  src={team1.avatar ? team1.avatar : logo}
                  style={{ width: "50px", height: "50px" }}
                  onError={(e) => {
                    e.currentTarget.onerror = null;
                    e.currentTarget.src = errorImage;
                  }}
                ></img>
                <h3 style={{ marginLeft: "10px", marginRight: "10px" }}>
                  <Link
                    style={{
                      color: "var(--bs-body-color)",
                      textDecoration: "none",
                    }}
                    to={`/team?id=${team1.team_id}`}
                  >
                    {team1.name}
                  </Link>
                </h3>
                <Badge bg="info">{team1.elo.toPrecision(4)}</Badge>
              </div>
            </Row>
            <Row>
              <div style={{ display: "flex", alignItems: "center" }}>
                <img
                  src={team2.avatar ? team2.avatar : logo}
                  style={{ width: "50px", height: "50px" }}
                  onError={(e) => {
                    e.currentTarget.onerror = null;
                    e.currentTarget.src = errorImage;
                  }}
                ></img>
                <h3 style={{ marginLeft: "10px", marginRight: "10px" }}>
                  <Link
                    style={{
                      color: "var(--bs-body-color)",
                      textDecoration: "none",
                    }}
                    to={`/team?id=${team2.team_id}`}
                  >
                    {team2.name}
                  </Link>
                </h3>
                <Badge bg="info">{team2.elo.toPrecision(4)}</Badge>
              </div>
            </Row>
          </Col>
          <Col style={{ marginRight: "1rem" }} className="text-end">
            <Row className="justify-content-end">
              {timeLeft.includes("d") ? (
                <h5>
                  {format(
                    new Date(match.scheduled_time * 1000),
                    "MMM do, h:mm aaa"
                  )}
                </h5>
              ) : (
                <h3>
                  {format(new Date(match.scheduled_time * 1000), "h:mm aaa")}
                </h3>
              )}
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
                <h6 className="d-none d-md-block">{timeLeft}</h6>
              )}
            </Row>
            <Row className="justify-content-end">
              {match.competition == "necc" ? (
                <Badge
                  className="mt-2"
                  bg="secondary"
                  style={{ maxWidth: "75px", fontSize: "1rem" }}
                >
                  NECC
                </Badge>
              ) : null}
              {match.competition == "playfly" ? (
                <Badge
                  className="mt-2"
                  bg="info"
                  style={{ maxWidth: "75px", fontSize: "1rem" }}
                >
                  PlayFly
                </Badge>
              ) : null}
              {match.competition == "playfly (playoff)" ? (
                <Badge
                  className="mt-2"
                  bg="primary"
                  style={{ maxWidth: "150px", fontSize: "1rem" }}
                >
                  PlayFly Playoff
                </Badge>
              ) : null}
            </Row>
          </Col>
        </Row>
        {expected_score ? (
          <>
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
                  team1.name + " " + Math.round(expected_score * 100) + "%"
                }
                variant="info"
              />
              <ProgressBar
                now={Math.round((1 - expected_score) * 100)}
                label={
                  team2.name +
                  " " +
                  Math.round((1 - expected_score) * 100) +
                  "%"
                }
                variant="primary"
              />
            </ProgressBar>
          </>
        ) : (
          <></>
        )}

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
          <Col>
            <Row style={{ marginBottom: "1rem" }}>
              <div style={{ display: "flex", alignItems: "center" }}>
                <img
                  src={team1.avatar ? team1.avatar : logo}
                  style={{ width: "50px", height: "50px" }}
                  onError={(e) => {
                    e.currentTarget.onerror = null;
                    e.currentTarget.src = errorImage;
                  }}
                ></img>
                <h4 style={{ marginLeft: "10px", marginRight: "10px" }}>
                  <Link
                    style={{
                      color: "var(--bs-body-color)",
                      textDecoration: "none",
                    }}
                    to={`/team?id=${team1.team_id}`}
                  >
                    {team1.name}
                  </Link>
                </h4>
                <Badge bg="info">{team1.elo.toPrecision(4)}</Badge>
              </div>
            </Row>
            <Row>
              <div style={{ display: "flex", alignItems: "center" }}>
                <img
                  src={team2.avatar ? team2.avatar : logo}
                  style={{ width: "50px", height: "50px" }}
                  onError={(e) => {
                    e.currentTarget.onerror = null;
                    e.currentTarget.src = errorImage;
                  }}
                ></img>
                <h4 style={{ marginLeft: "10px", marginRight: "10px" }}>
                  <Link
                    style={{
                      color: "var(--bs-body-color)",
                      textDecoration: "none",
                    }}
                    to={`/team?id=${team2.team_id}`}
                  >
                    {team2.name}
                  </Link>
                </h4>
                <Badge bg="info">{team2.elo.toPrecision(4)}</Badge>
              </div>
            </Row>
          </Col>
          <Col style={{ marginRight: "1rem" }} className="text-end">
            <Row className="justify-content-end">
              {format(
                new Date(match.scheduled_time * 1000),
                "MMM do, h:mm aaa"
              )}
            </Row>
            <Row className="justify-content-end mt-3">
              {match.competition === "necc" ? (
                <Badge
                  bg="secondary"
                  className="mb-1"
                  style={{ maxWidth: "75px", fontSize: "1rem" }}
                >
                  NECC
                </Badge>
              ) : null}
              {match.competition === "playfly" ? (
                <Badge bg="info" style={{ maxWidth: "75px", fontSize: "1rem" }}>
                  PlayFly
                </Badge>
              ) : null}
              {match.competition == "playfly (playoff)" ? (
                <Badge
                  className="mt-2"
                  bg="primary"
                  style={{ maxWidth: "150px", fontSize: "1rem" }}
                >
                  PlayFly Playoff
                </Badge>
              ) : null}
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

        {expected_score ? (
          <>
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
                  team1.name + " " + Math.round(expected_score * 100) + "%"
                }
                variant="info"
              />
              <ProgressBar
                now={Math.round((1 - expected_score) * 100)}
                label={
                  team2.name +
                  " " +
                  Math.round((1 - expected_score) * 100) +
                  "%"
                }
                variant="primary"
              />
            </ProgressBar>
          </>
        ) : (
          <></>
        )}
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
                src={team1.avatar ? team1.avatar : logo}
                style={{ width: "30px", height: "30px" }}
                onError={(e) => {
                  e.currentTarget.onerror = null;
                  e.currentTarget.src = errorImage;
                }}
              ></img>
              <h6 style={{ marginLeft: "10px", marginRight: "10px" }}>
                {team1.name}
              </h6>
              <Badge bg="info">{team1.elo.toPrecision(4)}</Badge>
            </div>
          </Row>
          <Row>
            <div style={{ display: "flex", alignItems: "center" }}>
              <img
                src={team2.avatar ? team2.avatar : logo}
                style={{ width: "30px", height: "30px" }}
                onError={(e) => {
                  e.currentTarget.onerror = null;
                  e.currentTarget.src = errorImage;
                }}
              ></img>
              <h6 style={{ marginLeft: "10px", marginRight: "10px" }}>
                {team2.name}
              </h6>
              <Badge bg="info">{team2.elo.toPrecision(4)}</Badge>
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
