import { Badge, Card, Container, Form } from "react-bootstrap";
import { Link } from "react-router-dom";
import { useState, useRef, useEffect } from "react";
import FlipMove from "react-flip-move";
import { forwardRef } from "react";
import { Team, EloHistory } from "../../types";
import { useQueryClient } from "@tanstack/react-query";
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
    const [team, setTeam] = useState<Team | null>(null);
    const queryClient = useQueryClient();

    useEffect(() => {
      async function fetchTeamData(team_id: string): Promise<void> {
        const team = await queryClient.fetchQuery({
          queryKey: ["team", team_id],
          queryFn: () => fetchTeam(team_id),
          staleTime: 1000 * 60 * 10,
        });
        setTeam(team);
      }

      fetchTeamData(team_id);
    }, [team_id]);

    if (!team) {
      return null;
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
  const [eloData, setEloData] = useState<GroupedEloHistory>({});
  const containerRef = useRef<HTMLDivElement>(null);

  function groupEloHistories(histories: EloHistory[]): {
    [team_id: string]: { elo: number; timestamp: number }[];
  } {
    return histories.reduce((acc, { team_id, elo, timestamp }) => {
      if (!acc[team_id]) {
        acc[team_id] = [];
      }
      acc[team_id].push({ elo, timestamp });
      return acc;
    }, {} as { [team_id: string]: { elo: number; timestamp: number }[] });
  }

  async function fetchEloHistory(): Promise<GroupedEloHistory> {
    const response = await fetch(`${apiBaseUrl}/get_elo_history`);
    const elo_history = await response.json();

    const eloHistoryGroups = groupEloHistories(elo_history);
    return eloHistoryGroups;
  }

  function getEloForMatchDay(
    _team: { team_id: string },
    matchDay: number
  ): number {
    const teamEloHistory = eloData[_team.team_id];
    if (!teamEloHistory || teamEloHistory.length === 0) {
      // Return a default value if no data exists; adjust as needed.
      return 0;
    }
    // If the requested matchDay exists, use it, otherwise use the last available entry.
    const entry =
      teamEloHistory[matchDay] ?? teamEloHistory[teamEloHistory.length - 1];
    return entry.elo;
  }

  function getRankChange(_team: { team_id: string }, matchDay: number): number {
    // get the rankings from the previous matchday
    const previousMatchDay = matchDay - 1;
    if (previousMatchDay < 0) {
      return 0;
    }
    const currentRanking = Object.entries(eloData).sort(
      ([team_a], [team_b]) =>
        getEloForMatchDay({ team_id: team_b }, matchDay) -
        getEloForMatchDay({ team_id: team_a }, matchDay)
    );
    // find the index of the team in the sorted array
    const teamIndex = currentRanking.findIndex(
      ([team_id]) => team_id === _team.team_id
    );
    // get the rankings from the previous matchday
    const previousRanking = Object.entries(eloData).sort(
      ([team_a], [team_b]) =>
        getEloForMatchDay({ team_id: team_b }, previousMatchDay) -
        getEloForMatchDay({ team_id: team_a }, previousMatchDay)
    );
    // find the index of the team in the sorted array
    const previousTeamIndex = previousRanking.findIndex(
      ([team_id]) => team_id === _team.team_id
    );
    // calculate the rank change
    return previousTeamIndex - teamIndex;
  }

  useEffect(() => {
    const fetchData = async () => {
      document.title = "CC - Rankings";
      const eloHistoryGroups = await fetchEloHistory();
      setEloData(eloHistoryGroups);
    };
    fetchData();
  }, []);

  const handleSliderChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    const value = event.target.valueAsNumber || Number(event.target.value);
    setSliderPosition(value);
    const quantizedValue = Math.round((value / 100) * totalMatchDays);
    setMatchDay(quantizedValue);

    if (containerRef.current) {
      containerRef.current.scrollTop = containerRef.current.scrollTop;
    }
  };

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
