import { Badge, Card, Container, Form } from "react-bootstrap";
import teamsElo from "../../../../cc-ranking/.dev/team_elo_history.json";
import { Link } from "react-router-dom";
import { useState, useRef } from "react";
import FlipMove from "react-flip-move";
import { forwardRef } from "react";

interface Team {
  name: string;
  roster: {
    player_id: string;
    nickname: string;
    avatar: string;
    membership: string;
    game_player_id: string;
    game_player_name: string;
    game_skill_level: number;
    anticheat_required: boolean;
  }[];
  faction_id: string;
  leader: string;
  avatar: string;
  substituted: boolean;
  type: string;
  elo: number;
  elo_history: {
    match_id: string | null;
    opponent_id: string;
    result: number;
    new_elo: number;
  }[];
}

interface RankingProps {
  team: Team;
  rank: number;
  elo: number;
  rankChange: number;
}

const Ranking = forwardRef<HTMLDivElement, RankingProps>(
  ({ team, rank, elo, rankChange }, ref) => {
    return (
      <Card className="mb-2" ref={ref}>
        <div className="d-flex justify-content-between align-items-center p-2">
          <div className="d-flex align-items-center">
            <h1 style={{ position: "absolute", left: "1rem" }}>{rank + 1}. </h1>
            <img
              src={team.avatar}
              alt={team.name}
              style={{
                width: "50px",
                height: "50px",
                marginLeft: "5rem",
                marginRight: "2rem",
              }}
            />

            <h3 className="ml-2 text-truncate">
              <Link
                style={{
                  color: "var(--bs-body-color)",
                  overflow: "hidden",
                  textOverflow: "ellipsis",
                  whiteSpace: "nowrap",
                  display: "block",
                  textDecoration: "none",
                }}
                to={`/team?id=${team.faction_id}`}
              >
                {team.name}
              </Link>
            </h3>
          </div>
          {rankChange != 0 ? (
            <Badge
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

  const handleSliderChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    const value = event.target.valueAsNumber || Number(event.target.value);
    setSliderPosition(value);
    const quantizedValue = Math.round((value / 100) * totalMatchDays);
    setMatchDay(quantizedValue);

    if (containerRef.current) {
      containerRef.current.scrollTop = containerRef.current.scrollTop;
    }
  };

  const getEloForMatchDay = (team: Team, matchDay: number) => {
    if (matchDay === 0) {
      return team.elo_history[0]?.new_elo ?? team.elo;
    }
    const history = team.elo_history.filter((entry) => entry.result !== -1);
    return history.length >= matchDay
      ? history[matchDay - 1]?.new_elo ?? team.elo
      : team.elo;
  };

  const getRankChange = (
    team: Team,
    currentRank: number,
    previousRankings: Team[]
  ) => {
    const previousRank = previousRankings.findIndex(
      (t) => t.faction_id === team.faction_id
    );
    if (matchDay === 0) {
      return 0;
    }
    return previousRank === -1 ? 0 : previousRank - currentRank;
  };

  const previousRankings = [...teamsElo].sort(
    (a, b) =>
      getEloForMatchDay(b, matchDay - 1) - getEloForMatchDay(a, matchDay - 1)
  );

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

        <FlipMove>
          {teamsElo
            .sort(
              (a, b) =>
                getEloForMatchDay(b, matchDay) - getEloForMatchDay(a, matchDay)
            )
            .map((team, index) => (
              <Ranking
                key={team.faction_id}
                team={team}
                elo={getEloForMatchDay(team, matchDay)}
                rank={index}
                rankChange={getRankChange(team, index, previousRankings)}
              />
            ))}
        </FlipMove>
      </Container>
    </>
  );
};

export default Rankings;
