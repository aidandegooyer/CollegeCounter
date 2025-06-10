import React, { useEffect } from "react";
import { Container, Row, Col, Spinner, Button } from "react-bootstrap";
import { Link, useLocation } from "react-router-dom";
import { Player, Team } from "../../types";
import { useQuery } from "@tanstack/react-query";
import "./PlayerPage.css";
import silhouette from "../../assets/player_silhouette.png";
import FaceitIcon from "../../assets/faceit.svg";
const apiBaseUrl =
  import.meta.env.VITE_API_BASE_URL || "https://api.collegecounter.org";

const fetchPlayer = async (playerId: string): Promise<Player> => {
  const response = await fetch(`${apiBaseUrl}/player/${playerId}`);
  return response.json();
};

const fetchTeam = async (team_id: string): Promise<Team> => {
  const response = await fetch(`${apiBaseUrl}/team/${team_id}`);
  return response.json();
};

const PlayerPage: React.FC = () => {
  const query = new URLSearchParams(useLocation().search);
  const playerId = query.get("id");

  const {
    data: player,
    isLoading: playerLoading,
    error: playerErrorObj,
    isError: playerError,
  } = useQuery<Player>({
    queryKey: ["player", playerId],
    queryFn: () => fetchPlayer(playerId!),
    staleTime: 1000 * 60 * 10,
  });

  const {
    data: team,
    isLoading: teamLoading,
    error: teamErrorObj,
    isError: teamError,
  } = useQuery<Team>({
    queryKey: ["team", player?.team_id],
    queryFn: () => fetchTeam(player?.team_id!),
    staleTime: 1000 * 60 * 10,
    enabled: !!player?.team_id,
  });
  useEffect(() => {
    document.title = `${player?.nickname} - College Counter`;
  }, [player]);

  const handlePlayerClickFaceit = () => {
    // open new tab with player profile
    window.open(
      `https://www.faceit.com/en/players/${player?.nickname}`,
      "_blank"
    );
  };

  const handlePlayerClickSteam = () => {
    // open new tab with player profile
    window.open(
      `https://steamcommunity.com/profiles/${player?.steam_id}`,
      "_blank"
    );
  };
  if (playerLoading || teamLoading) {
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
  }
  if (playerError || teamError) {
    return (
      <Container
        style={{ marginTop: "0.5rem", padding: "0 1rem" }}
        className="text-center"
      >
        <h1>
          Error: {playerErrorObj?.message} {teamErrorObj?.message}
        </h1>
      </Container>
    );
  }

  return (
    <Container style={{ marginTop: "50px", maxWidth: "800px" }}>
      <Row className="justify-content-between align-items-center">
        <Col xs="auto" className="text-start">
          <h1>{player?.nickname}</h1>
          <div className="d-flex align-items-center">
            {team?.leader === player?.player_id ? (
              <i
                className="bi bi-star"
                style={{
                  fontSize: "1rem",
                  color: "gold",
                  marginRight: "0.5rem",
                }}
              />
            ) : (
              ""
            )}
            <Link
              to="/team?id=${team?.team_id}`}>"
              style={{ textDecoration: "none", color: "var(--bs-body-color)" }}
            >
              <h3>{team?.name}</h3>
            </Link>
          </div>
          <span>
            <Button
              variant="outline-light"
              style={{ marginRight: "1rem" }}
              onClick={handlePlayerClickSteam}
            >
              <i className="bi bi-steam"></i>
            </Button>
            <Button variant="outline-light" onClick={handlePlayerClickFaceit}>
              <img
                src={FaceitIcon}
                alt="Faceit Icon"
                className="faceit-icon"
                style={{ width: "1em", height: "1em" }}
              />
            </Button>
          </span>
        </Col>
        <Col xs="auto" className="text-end">
          <div
            style={{
              position: "relative",
              width: "250px",
              height: "250px",
            }}
          >
            <img
              src={team?.avatar}
              alt="Team Avatar"
              style={{ width: "250px", height: "250px", borderRadius: "5%" }}
            />
            {player?.avatar?.includes("faceit") || !player?.avatar ? (
              <img
                src={silhouette}
                alt="Player Avatar"
                style={{
                  width: "250px",
                  height: "250px",
                  position: "absolute",
                  top: 0,
                  left: 0,
                  zIndex: 1,
                }}
              />
            ) : (
              <img
                src={player?.avatar}
                alt="Player Avatar"
                style={{
                  width: "250px",
                  height: "250px",
                  position: "absolute",
                  top: 0,
                  left: 0,
                  zIndex: 1,
                  borderRadius: "5%",
                }}
              />
            )}
          </div>
        </Col>
      </Row>

      <h4 style={{ marginTop: "5rem" }}>Stats coming soon...</h4>
    </Container>
  );
};

export default PlayerPage;
