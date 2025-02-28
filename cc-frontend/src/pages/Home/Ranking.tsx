import React from "react";
import { Button, Container, ListGroup } from "react-bootstrap";

const RankingItem = ({ team, index }: { team: string; index: number }) => (
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
      {index + 1}. {team}
    </span>
    <img
      src="holder.js/30x30"
      alt={`${team} logo`}
      style={{ height: "30px" }}
    />
  </ListGroup.Item>
);

const Ranking: React.FC = () => {
  const teams = [
    "Team A",
    "Team B",
    "Team C",
    "Team D",
    "Team E",
    "Team F",
    "Team G",
    "Team H",
    "Team I",
    "Team J",
  ];

  return (
    <Container
      style={{
        borderLeft: "1px solid #dee2e6",
        borderRight: "1px dotted #dee2e6",
        position: "sticky",
        top: "5%",
        zIndex: 1000,
      }}
    >
      <h3 style={{ fontSize: "1.5rem" }}>Team Rankings</h3>
      <ListGroup variant="flush">
        {teams.map((team, index) => (
          <RankingItem key={team} team={team} index={index} />
        ))}
      </ListGroup>
      <div
        style={{ display: "flex", justifyContent: "center", marginTop: "10px" }}
      >
        <Button variant="info">
          View More
          <i className="bi bi-arrow-right" style={{ marginLeft: "5px" }}></i>
        </Button>
      </div>
    </Container>
  );
};

export default Ranking;
