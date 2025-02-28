import React from "react";
import { Button, Card, Col, Container, Row } from "react-bootstrap";
import { Link } from "react-router-dom";

const Match = ({
  key,
  team1,
  team2,
  date,
  time,
}: {
  key: number;
  team1: string;
  team2: string;
  date: string;
  time: string;
}) => (
  <Card key={key} style={{ marginBottom: "10px" }}>
    <Card.Body>
      <Card.Title>
        {team1} vs {team2}
      </Card.Title>
      <Card.Text>
        {date}, {time}pm
      </Card.Text>
      <div
        style={{
          display: "flex",
          justifyContent: "center",
          marginTop: "10px",
        }}
      >
        <Button variant="primary">View Match</Button>
      </div>
    </Card.Body>
  </Card>
);

const MatchesWidget: React.FC = () => {
  const upcomingMatches = [
    {
      id: 1,
      team1: "Team A",
      team2: "Team B",
      date: "2025-10-01",
      time: "12:00",
    },
    {
      id: 2,
      team1: "Team C",
      team2: "Team D",
      date: "2025-10-02",
      time: "12:00",
    },
    {
      id: 3,
      team1: "Team E",
      team2: "Team F",
      date: "2025-10-03",
      time: "12:00",
    },
    {
      id: 4,
      team1: "Team G",
      team2: "Team H",
      date: "2025-10-04",
      time: "12:00",
    },
  ];

  return (
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
          {upcomingMatches.map((match) => (
            <Match
              key={match.id}
              team1={match.team1}
              team2={match.team2}
              date={match.date}
              time={match.time}
            ></Match>
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
  );
};

export default MatchesWidget;
