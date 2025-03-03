import React from "react";
import { Badge, Button, Container, ListGroup } from "react-bootstrap";
import { Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { Team } from "../../types";

const fetchTopTeams = async () => {
  const response = await fetch("http://localhost:8889/top10");
  const data = await response.json();
  return data;
};

const RankingItem = ({ team, index }: { team: Team; index: number }) => (
  <ListGroup.Item
    style={{
      marginBottom: "10px",
      fontSize: "16px",
      display: "flex",
      justifyContent: "space-between",
      alignItems: "center",
      marginRight: "0",
    }}
  >
    <span>
      <strong>{index + 1}.</strong>
      <Link
        to={`/team?id=${team.team_id}`}
        style={{
          overflow: "hidden",
          textOverflow: "ellipsis",
          whiteSpace: "nowrap",
          display: "inline",
          marginLeft: "5px",
          color: "var(--bs-body-color)",
        }}
      >
        {team.name}
      </Link>
    </span>
    <div>
      <img
        src={team.avatar}
        alt={`logo`}
        style={{ height: "30px", marginRight: "10px" }}
      />
      <Badge bg="primary">{team.elo.toPrecision(4)}</Badge>
    </div>
  </ListGroup.Item>
);

const RankingWidget: React.FC = () => {
  const {
    data: teams = [],
    isLoading,
    isError,
  } = useQuery({ queryKey: ["topTeams"], queryFn: fetchTopTeams });

  if (isLoading) {
    return <div>Loading...</div>;
  }

  if (isError) {
    return <div>Error loading teams</div>;
  }

  return (
    <Container
      style={{
        borderLeft: "1px solid #dee2e6",
        borderRight: "1px dotted #dee2e6",
        position: "sticky",
        top: "60px",
        zIndex: 1000,
      }}
    >
      <h3 style={{ fontSize: "1.5rem" }}>Team Rankings</h3>
      <ListGroup variant="flush">
        {teams.map((team: Team, index: number) => (
          <RankingItem key={team.name} team={team} index={index} />
        ))}
      </ListGroup>
      <div
        style={{ display: "flex", justifyContent: "center", marginTop: "10px" }}
      >
        <Button variant="info">
          <Link
            to="/rankings"
            style={{ color: "white", textDecoration: "none" }}
          >
            View More
            <i className="bi bi-arrow-right" style={{ marginLeft: "5px" }}></i>
          </Link>
        </Button>
      </div>
    </Container>
  );
};

export default RankingWidget;
