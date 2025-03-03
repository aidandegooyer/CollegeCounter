import { Container } from "react-bootstrap";
import { useEffect, useState } from "react";
import ResultCard from "./ResultCard";
import { useQueryClient } from "@tanstack/react-query";
import { Match, Team } from "../../types";

const fetchTeam = async (teamId: string): Promise<Team> => {
  const response = await fetch(`http://localhost:8889/team/${teamId}`);
  return response.json();
};

const Results = () => {
  const [matches, setMatches] = useState<Match[]>([]);

  const queryClient = useQueryClient();

  useEffect(() => {
    const fetchMatches = async () => {
      const response = await fetch("http://localhost:8889/results");
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
      setMatches(matchesWithTeams);
    };

    fetchMatches();
  }, [queryClient]);

  interface RenderMatchesProps {
    matches: Match[];
  }

  const renderMatches = ({ matches }: RenderMatchesProps) => {
    if (matches.length === 0) {
      return <p>No matches to display</p>;
    }

    const sortedMatches = matches.sort(
      (a, b) => b.scheduled_time - a.scheduled_time
    );
    return sortedMatches.map((match: Match) => (
      <ResultCard key={match.match_id} match={match} />
    ));
  };

  return (
    <Container
      style={{ marginTop: "0.5rem", maxWidth: "1300px", padding: "0 1rem" }}
    >
      <Container style={{ maxWidth: "800px" }}>
        <h1 className="text-center">Results</h1>
        {matches.length === 0 ? (
          <p>No matches to display</p>
        ) : (
          Object.entries(
            matches.reduce((acc, match) => {
              const date = new Date(
                match.scheduled_time * 1000
              ).toLocaleDateString();
              if (!acc[date]) acc[date] = [];
              acc[date].push(match);
              return acc;
            }, {} as Record<string, Match[]>)
          )
            .sort(
              ([dateA], [dateB]) =>
                new Date(dateB).getTime() - new Date(dateA).getTime()
            )
            .map(([date, matches]) => (
              <div key={date}>
                <h2>
                  {new Date(date).toLocaleDateString("en-US", {
                    year: "numeric",
                    month: "long",
                    day: "numeric",
                  })}
                </h2>
                {renderMatches({ matches })}
              </div>
            ))
        )}
      </Container>
    </Container>
  );
};

export default Results;
