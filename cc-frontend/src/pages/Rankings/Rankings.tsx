import { Alert, Badge, Card, Container, Form, Spinner } from "react-bootstrap";
import { Link } from "react-router-dom";
import { useState, useRef, useEffect } from "react";
import FlipMove from "react-flip-move";
import { forwardRef } from "react";
import { Team, EloHistory } from "../../types";
import { useQuery } from "@tanstack/react-query";
import errorImage from "../../assets/error-profile-pic.png";

const apiBaseUrl =
  import.meta.env.VITE_API_BASE_URL || "https://api.collegecounter.org";

interface GroupedEloHistory {
  [team_id: string]: {
    elo: number;
    timestamp: number;
  }[];
}

interface RankingProps {
  team_id: string;
  rank: number;
  elo: number;
  rankChange: number;
}

const fetchTeam = async (teamId: string): Promise<Team> => {
  const response = await fetch(`${apiBaseUrl}/team/${teamId}`);
  return response.json();
};

const Ranking = forwardRef<HTMLDivElement, RankingProps>(
  ({ team_id, rank, elo, rankChange }, ref) => {
    const {
      data: team,
      isPending: teamPending,
      isError: teamError,
      error: teamErrorObj,
    } = useQuery({
      queryKey: ["team", team_id],
      queryFn: () => fetchTeam(team_id),
      staleTime: 1000 * 60 * 10,
    });

    if (teamPending) {
      return (
        <Card className="mb-2" ref={ref}>
          <div className="d-flex justify-content-between align-items-center p-2">
            <div className="d-flex align-items-center">
              <h1 style={{ position: "absolute", left: "1rem" }}>
                {rank + 1}.{" "}
              </h1>
              <Spinner />

              <h3 className="ml-2 text-truncate">Loading...</h3>
            </div>

            <Badge style={{ position: "absolute", right: "1rem" }} bg="primary">
              <h5 className="mb-0">...</h5>
            </Badge>
          </div>
        </Card>
      );
    }

    if (teamError) {
      return <div>Error: {teamErrorObj.message}</div>;
    }

    return (
      <Card className="mb-2" ref={ref}>
        <div className="d-flex justify-content-between align-items-center p-2">
          <div className="d-flex align-items-center">
            <h1 style={{ position: "absolute", left: "1rem" }}>{rank + 1}. </h1>
            <img
              className="d-none d-sm-block"
              src={team.avatar}
              alt={team.name}
              onError={(e) => {
                e.currentTarget.onerror = null;
                e.currentTarget.src = errorImage;
              }}
              style={{
                width: "50px",
                height: "50px",
                marginLeft: "5rem",
              }}
            />

            <h3 className="ml-2 text-truncate">
              <Link
                style={{
                  marginLeft: "3rem",
                  color: "var(--bs-body-color)",
                  overflow: "hidden",
                  textOverflow: "ellipsis",
                  whiteSpace: "nowrap",
                  display: "block",
                  textDecoration: "none",
                }}
                to={`/team?id=${team.team_id}`}
              >
                {team.name}
              </Link>
            </h3>
          </div>
          {rankChange != 0 ? (
            <Badge
              className="d-none d-sm-block"
              bg={
                rankChange > 0
                  ? "success"
                  : rankChange < 0
                  ? "danger"
                  : "secondary"
              }
              style={{
                marginRight: "5rem",
                fontSize: "1.2rem",
                position: "absolute",
                right: "0.5rem",
              }}
            >
              {rankChange > 0 ? (
                <i className="bi bi-caret-up-fill" />
              ) : rankChange < 0 ? (
                <i className="bi bi-caret-down-fill" />
              ) : (
                <i className="bi bi-dash" />
              )}
              {Math.abs(rankChange)}
            </Badge>
          ) : (
            <div style={{ marginRight: "5rem" }}></div>
          )}
          <Badge style={{ position: "absolute", right: "1rem" }} bg="primary">
            <h5 className="mb-0">{elo.toPrecision(4)}</h5>
          </Badge>
        </div>
      </Card>
    );
  }
);

const Rankings = () => {
  const totalMatchDays = 5;
  const [matchDay, setMatchDay] = useState(totalMatchDays);
  const [sliderPosition, setSliderPosition] = useState(100);
  const containerRef = useRef<HTMLDivElement>(null);

  // Groups a flat array of EloHistory into an object keyed by team_id
  function groupEloHistories(histories: EloHistory[]): GroupedEloHistory {
    return histories.reduce((acc, { team_id, elo, timestamp }) => {
      if (!acc[team_id]) {
        acc[team_id] = [];
      }
      acc[team_id].push({ elo, timestamp });
      return acc;
    }, {} as GroupedEloHistory);
  }

  // Fetch Elo history and group it by team
  async function fetchEloHistory(): Promise<GroupedEloHistory> {
    const response = await fetch(`${apiBaseUrl}/get_elo_history`);
    if (!response.ok) {
      throw new Error("Error fetching elo history");
    }
    const elo_history: EloHistory[] = await response.json();
    return groupEloHistories(elo_history);
  }

  // Use TanStack Query to fetch the Elo history data
  const {
    data: eloData,
    isLoading,
    isError,
    error,
  } = useQuery({
    queryKey: ["eloHistory"],
    queryFn: fetchEloHistory,
    staleTime: 1, //1000 * 60 * 10, // 10 minutes
  });

  // Return the elo for a team for a given match day.
  // If the requested matchDay doesn't exist, fallback to the last available entry.
  function getEloForMatchDay(
    _team: { team_id: string },
    matchDay: number
  ): number {
    if (
      !eloData ||
      !eloData[_team.team_id] ||
      eloData[_team.team_id].length === 0
    ) {
      return 0;
    }
    const teamEloHistory = eloData[_team.team_id];
    const entry =
      teamEloHistory[matchDay] ?? teamEloHistory[teamEloHistory.length - 1];
    return entry.elo;
  }

  // Calculate the rank change for a team between the current match day and the previous one.
  function getRankChange(_team: { team_id: string }, matchDay: number): number {
    if (!eloData) return 0;
    const previousMatchDay = matchDay - 1;
    if (previousMatchDay < 0) return 0;
    // Sort teams by elo descending for the current match day.
    const currentRanking = Object.entries(eloData).sort(
      ([teamA], [teamB]) =>
        getEloForMatchDay({ team_id: teamB }, matchDay) -
        getEloForMatchDay({ team_id: teamA }, matchDay)
    );
    const teamIndex = currentRanking.findIndex(
      ([team_id]) => team_id === _team.team_id
    );
    // Sort teams by elo descending for the previous match day.
    const previousRanking = Object.entries(eloData).sort(
      ([teamA], [teamB]) =>
        getEloForMatchDay({ team_id: teamB }, previousMatchDay) -
        getEloForMatchDay({ team_id: teamA }, previousMatchDay)
    );
    const previousTeamIndex = previousRanking.findIndex(
      ([team_id]) => team_id === _team.team_id
    );
    return previousTeamIndex - teamIndex;
  }

  // Set the document title once on mount.
  useEffect(() => {
    document.title = "CC - Rankings";
  }, []);

  // Handle slider changes by quantizing the slider value to a match day.
  const handleSliderChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    const value = event.target.valueAsNumber || Number(event.target.value);
    setSliderPosition(value);
    const quantizedValue = Math.round((value / 100) * totalMatchDays);
    setMatchDay(quantizedValue);

    if (containerRef.current) {
      containerRef.current.scrollTop = containerRef.current.scrollTop;
    }
  };

  // Render a loading or error state if necessary.
  if (isLoading) {
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

  if (isError) {
    return (
      <Alert variant="danger">
        {" "}
        <strong>Error: </strong>
        {error?.message}
      </Alert>
    );
  }

  return (
    <>
      <Container
        ref={containerRef}
        style={{ marginTop: "0.5rem", maxWidth: "800px", padding: "0 1rem" }}
      >
        <h1 className="text-center">Rankings</h1>
        <div
          style={{
            position: "sticky",
            top: "55px",
            zIndex: 1,
            background: "var(--bs-body-bg)",
          }}
        >
          {matchDay === 0 ? (
            <h3 className="text-center">Pre-Season</h3>
          ) : (
            <h3 className="text-center">Matchday {matchDay}</h3>
          )}
          <div className="d-flex justify-content-center">
            <Form.Range
              value={sliderPosition}
              className="justify-content-center"
              style={{ maxWidth: "50%", marginBottom: "1rem" }}
              onChange={handleSliderChange}
            />
          </div>
        </div>

        {
          <FlipMove>
            {eloData &&
              Object.entries(eloData)
                .sort(
                  ([team_a], [team_b]) =>
                    getEloForMatchDay({ team_id: team_b }, matchDay) -
                    getEloForMatchDay({ team_id: team_a }, matchDay)
                )
                .map(([team_id], index) => (
                  <Ranking
                    key={team_id}
                    team_id={team_id} // or pass the full team data if available
                    elo={getEloForMatchDay({ team_id: team_id }, matchDay)}
                    rank={index}
                    rankChange={getRankChange({ team_id: team_id }, matchDay)}
                  />
                ))}
          </FlipMove>
        }
      </Container>
    </>
  );
};

export default Rankings;
