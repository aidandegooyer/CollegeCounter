import React from "react";
import { Badge, Button, Container, ListGroup } from "react-bootstrap";
import { Link } from "react-router-dom";

const RankingItem = ({ team, index }: { team: any; index: number }) => (
  <ListGroup.Item
    style={{
      marginBottom: "10px",
      fontSize: "16px",
      display: "flex",
      justifyContent: "space-between",
      alignItems: "center",
    }}
  >
    <span>
      <strong>{index + 1}.</strong> {team.name}
    </span>
    <div>
      <img
        src="holder.js/30x30"
        alt={`${team.name} logo`}
        style={{ height: "30px", marginRight: "10px" }}
      />
      <Badge bg="primary">{team.elo}</Badge>
    </div>
  </ListGroup.Item>
);

const RankingWidget: React.FC = () => {
  const teams = [
    { name: "Team A", elo: 2000 },
    { name: "Team B", elo: 1950 },
    { name: "Team C", elo: 1900 },
    { name: "Team D", elo: 1850 },
    { name: "Team E", elo: 1800 },
    { name: "Team F", elo: 1750 },
    { name: "Team G", elo: 1700 },
    { name: "Team H", elo: 1650 },
    { name: "Team I", elo: 1600 },
    { name: "Team J", elo: 1550 },
  ];

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
        {teams.map((team, index) => (
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
