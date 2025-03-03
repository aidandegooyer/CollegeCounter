import { Container, Row, Col } from "react-bootstrap";
import { useEffect, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import MatchCard from "./MatchCard";
import { Match, Team } from "../../types";

const fetchTeam = async (teamId: string): Promise<Team> => {
  const response = await fetch(`http://localhost:8889/team/${teamId}`);
  return response.json();
};

const Matches = () => {
  const [todayMatches, setTodayMatches] = useState<Match[]>([]);
  const [thisWeekMatches, setThisWeekMatches] = useState<Match[]>([]);
  const [otherMatches, setOtherMatches] = useState<Match[]>([]);

  const queryClient = useQueryClient();

  useEffect(() => {
    const fetchMatches = async () => {
      const response = await fetch("http://localhost:8889/upcoming");
      const matches: Match[] = await response.json();

      const matchesWithTeams = await Promise.all(
        matches.map(async (match) => {
          const team1 = await queryClient.fetchQuery({
            queryKey: ["team", match.team1_id],
            queryFn: () => fetchTeam(match.team1_id),
          });
          const team2 = await queryClient.fetchQuery({
            queryKey: ["team", match.team2_id],
            queryFn: () => fetchTeam(match.team2_id),
          });
          return { ...match, teams: { team1, team2 } };
        })
      );

      const today = new Date();
      const endOfToday = new Date(today);
      endOfToday.setHours(23, 59, 59, 999);
      today.setHours(0, 0, 0, 0);

      const endOfWeek = new Date(today);
      endOfWeek.setDate(today.getDate() + 7);
      endOfWeek.setHours(23, 59, 59, 999);

      const todayMatchesTemp: Match[] = [];
      const thisWeekMatchesTemp: Match[] = [];
      const otherMatchesTemp: Match[] = [];

      matchesWithTeams.forEach((match) => {
        const matchDate = new Date(match.scheduled_time * 1000);
        if (matchDate >= today && matchDate <= endOfToday) {
          todayMatchesTemp.push(match);
        } else if (matchDate > endOfToday && matchDate <= endOfWeek) {
          thisWeekMatchesTemp.push(match);
        } else if (matchDate > endOfWeek) {
          otherMatchesTemp.push(match);
        }
      });

      todayMatchesTemp.sort((a, b) => a.scheduled_time - b.scheduled_time);
      thisWeekMatchesTemp.sort((a, b) => a.scheduled_time - b.scheduled_time);
      otherMatchesTemp.sort((a, b) => a.scheduled_time - b.scheduled_time);

      setTodayMatches(todayMatchesTemp);
      setThisWeekMatches(thisWeekMatchesTemp);
      setOtherMatches(otherMatchesTemp);
    };

    fetchMatches();
  }, [queryClient]);

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
        {renderMatches({ matches: thisWeekMatches, thisweek: true })}
        <h3>Other</h3>
        {renderMatches({ matches: otherMatches, other: true })}
      </Container>
    </Container>
  );
};

export default Matches;
