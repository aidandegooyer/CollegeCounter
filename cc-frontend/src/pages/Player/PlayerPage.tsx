import React from "react";
import { Container, Row, Col, Button, Spinner } from "react-bootstrap";
import { useLocation } from "react-router-dom";
import { Player } from "../../types";
import { useQuery } from "@tanstack/react-query";
const apiBaseUrl =
  import.meta.env.VITE_API_BASE_URL || "https://api.collegecounter.org";

const fetchPlayer = async (playerId: string): Promise<Player> => {
  const response = await fetch(`${apiBaseUrl}/player/${playerId}`);
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

  const handlePlayerClick = () => {
    // open new tab with player profile
    window.open(
      `https://www.faceit.com/en/players/${player?.nickname}`,
      "_blank"
    );
  };
  return (
    <Container
      className="d-flex justify-content-center align-items-center"
      style={{ marginTop: "50px", height: "calc(80vh - 200px)" }}
    >
      <Row>
        <Col className="text-center">
          <h1>Still working...</h1>
          <h2>Player pages are coming soon</h2>
          <p>In the meantime, you can view the player's Faceit profile</p>

          {playerLoading || playerError || playerErrorObj ? (
            <Spinner />
          ) : (
            <Button variant="primary" onClick={handlePlayerClick}>
              View Profile
            </Button>
          )}
        </Col>
      </Row>
    </Container>
  );
};

export default PlayerPage;
