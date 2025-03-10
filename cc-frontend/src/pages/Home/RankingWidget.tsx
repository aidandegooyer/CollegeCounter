import React from "react";
import { Button, Container, ListGroup } from "react-bootstrap";
import { Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { Team } from "../../types";
import logo from "../../assets/0.5x/C Logo@0.5x.png";
const apiBaseUrl =
  import.meta.env.VITE_API_BASE_URL || "https://api.collegecounter.org";

const fetchTopTeams = async () => {
  const response = await fetch(`${apiBaseUrl}/top10`);
  const data = await response.json();
  return data;
};

const RankingItem = ({ team, index }: { team: Team; index: number }) => (
  <ListGroup.Item
    style={{
      display: "flex",
      alignItems: "center",
      justifyContent: "space-between",
      textOverflow: "ellipsis",
      fontSize: "16px",
      padding: "10px 15px",
      whiteSpace: "nowrap", // Ensures all items stay inline
      overflow: "hidden", // Prevents content from overflowing
    }}
  >
    {/* Left side: Index + Avatar + Name */}
    <div
      style={{
        display: "flex",
        alignItems: "center",
        gap: "10px",
        flexGrow: 1,
      }}
    >
      <strong>{index + 1}.</strong>
      <img
        src={team.avatar ? team.avatar : logo}
        alt={`logo`}
        style={{
          height: "40px",
          borderRadius: "5px",
          backgroundColor: "white",
        }}
      />
      <Link
        to={`/team?id=${team.team_id}`}
        style={{
          flexGrow: 1, // Allows the link to take up available space
          overflow: "hidden",
          textOverflow: "ellipsis",
          whiteSpace: "nowrap",
          color: "var(--bs-body-color)",
        }}
      >
        {team.name}
      </Link>
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
      <h3>Team Rankings</h3>
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
