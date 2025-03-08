import { Container, Row, Col, Spinner, Alert } from "react-bootstrap";
import { useEffect, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import MatchCard from "./MatchCard";
import { Match } from "../../types";
const apiBaseUrl =
  import.meta.env.VITE_API_BASE_URL || "https://api.collegecounter.org";

const fetchMatches = async (): Promise<Match[]> => {
  const response = await fetch(`${apiBaseUrl}/upcoming`);
  return response.json();
};

const Matches = () => {
  const [todayMatches, setTodayMatches] = useState<Match[]>([]);
  const [thisWeekMatches, setThisWeekMatches] = useState<Match[]>([]);
  const [otherMatches, setOtherMatches] = useState<Match[]>([]);

  useEffect(() => {
    document.title = "CC - Matches";
  }, []);

  const {
    data: matches,
    isPending: matchesLoading,
    isError: matchesError,
    error: matchesErrorObj,
  } = useQuery({
    queryKey: ["matches"],
    queryFn: fetchMatches,
    staleTime: 1000 * 60 * 10,
  });

  useEffect(() => {
    if (matches) {
      const today = new Date();
      const startOfWeek = new Date(today);
      startOfWeek.setDate(today.getDate());
      const endOfWeek = new Date(today);
      endOfWeek.setDate(today.getDate() + 6);

      const todayMatches = matches.filter((match) => {
        const matchDate = new Date(match.scheduled_time * 1000); // Convert Unix timestamp to Date
        return matchDate.toDateString() === new Date().toDateString();
      });

      const thisWeekMatches = matches.filter((match) => {
        const matchDate = new Date(match.scheduled_time * 1000); // Convert Unix timestamp to Date
        return (
          matchDate >= startOfWeek &&
          matchDate <= endOfWeek &&
          matchDate.toDateString() !== new Date().toDateString()
        );
      });

      const otherMatches = matches.filter((match) => {
        const matchDate = new Date(match.scheduled_time * 1000); // Convert Unix timestamp to Date
        return matchDate > endOfWeek;
      });

      setTodayMatches(todayMatches);
      setThisWeekMatches(thisWeekMatches);
      setOtherMatches(otherMatches);
    }
  }, [matches, matchesLoading]);

  if (matchesLoading) {
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

  if (matchesError) {
    return (
      <Alert variant="danger">
        {" "}
        <strong>Error: </strong>
        {matchesErrorObj?.message}
      </Alert>
    );
  }

  interface RenderMatchesProps {
    matches: Match[];
    today?: boolean;
    thisweek?: boolean;
    other?: boolean;
  }

  const renderMatches = ({
    matches,
    today,
    thisweek,
    other,
  }: RenderMatchesProps) => {
    if (matches.length === 0) {
      return <p>No matches to display</p>;
    }
    if (other) {
      return (
        <Row>
          {matches.map((match: Match) => (
            <Col key={match.match_id} md={6}>
              <MatchCard match={match} />
            </Col>
          ))}
        </Row>
      );
    }

    return matches.map((match: Match) => (
      <MatchCard
        key={match.match_id}
        match={match}
        today={today}
        thisweek={thisweek}
      />
    ));
  };

  return (
    <Container
      style={{ marginTop: "0.5rem", maxWidth: "1300px", padding: "0 1rem" }}
    >
      <Container style={{ maxWidth: "800px" }}>
        <h1 className="text-center">Upcoming Matches</h1>
        <h3>Today</h3>
        {renderMatches({ matches: todayMatches, today: true })}
        <h3>This Week</h3>
        {todayMatches.length === 0 &&
          thisWeekMatches.length > 0 &&
          renderMatches({ matches: [thisWeekMatches[0]], today: true })}
        {todayMatches.length != 0 &&
          thisWeekMatches.length > 0 &&
          renderMatches({ matches: [thisWeekMatches[0]], thisweek: true })}
        {renderMatches({ matches: thisWeekMatches.slice(1), thisweek: true })}
        <h3>Other</h3>
        {renderMatches({ matches: otherMatches, other: true })}
      </Container>
    </Container>
  );
};

export default Matches;
