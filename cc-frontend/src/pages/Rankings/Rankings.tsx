import { Badge, Card, Container } from "react-bootstrap";
import matchesList from "../../../../cc-ranking/.dev/upcoming.json";
import { Link } from "react-router-dom";

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
}

interface RankingProps {
  team: Team;
  rank: number;
  elo: number;
}

const Ranking = ({ team, rank, elo }: RankingProps) => {
  // generate a random number between 1 and 5
  const random = Math.floor(Math.random() * 5) + 1;
  // and a random boolean value
  const isPrime = Math.random() < 0.5;

  return (
    <Card className="mb-2">
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
          <Link to={`/team?id=${team.faction_id}`}>
            <h2 style={{ color: "white" }} className="ml-2 text-truncate">
              {team.name}
            </h2>
          </Link>
        </div>
        <div className="d-flex align-items-center">
          <Badge
            className="d-none d-md-block"
            bg={isPrime ? "success" : "danger"}
            style={{ marginRight: "4rem", fontSize: "1.2rem" }}
          >
            {isPrime ? (
              <i className="bi bi-caret-up-fill" />
            ) : (
              <i className="bi bi-caret-down-fill" />
            )}
            {random}
          </Badge>
          <Badge style={{ position: "absolute", right: "1rem" }} bg="primary">
            <h5 className="mb-0">{elo}</h5>
          </Badge>
        </div>
      </div>
    </Card>
  );
};

const Rankings = () => {
  const teamsMap = new Map<string, Team>();

  matchesList.forEach((match) => {
    teamsMap.set(match.teams.faction1.faction_id, match.teams.faction1);
    teamsMap.set(match.teams.faction2.faction_id, match.teams.faction2);
  });

  const uniqueTeams = Array.from(teamsMap.values());

  function calculateTeamLevel(team: Team) {
    let total = 0;
    team.roster.forEach((player) => {
      total += player.game_skill_level;
    });
    return total / 5;
  }

  return (
    <Container
      style={{ marginTop: "0.5rem", maxWidth: "800px", padding: "0 1rem" }}
    >
      <h1 className="text-center">Rankings</h1>
      <h3 className="text-center">Week of March 2, 2025</h3>
      {uniqueTeams
        .map((team) => ({
          team,
          elo: calculateTeamLevel(team),
        }))
        .sort((a, b) => b.elo - a.elo)
        .map(({ team, elo }, index) => (
          <Ranking key={team.faction_id} team={team} elo={elo} rank={index} />
        ))}
    </Container>
  );
};

export default Rankings;
