import { Button, Card, Image, Container, Badge } from "react-bootstrap";
import matchesList from "../../../../cc-ranking/.dev/upcoming.json";
import { useLocation } from "react-router-dom";

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

interface PlayerProps {
  nickname: string;
  avatar: string;
  level: number;
}

const Player: React.FC<PlayerProps> = ({ nickname, avatar, level }) => {
  const handlePlayerClick = () => {
    // open new tab with player profile
    window.open(`https://www.faceit.com/en/players/${nickname}`);
  };

  const getLevelColor = (level: number) => {
    if (level < 3) {
      return "secondary";
    } else if (level < 6) {
      return "success";
    } else if (level < 8) {
      return "warning";
    } else if (level < 10) {
      return "primary";
    } else {
      return "danger";
    }
  };

  return (
    <Card style={{ width: "150px", marginRight: "1rem" }}>
      <Card.Img variant="top" src={avatar} />
      <Card.Title
        className="text-center"
        style={{ fontSize: "1.5rem", marginTop: "1rem" }}
      >
        {nickname}
      </Card.Title>
      <div className="d-flex justify-content-center">
        <Badge bg={getLevelColor(level)} style={{ width: "70px" }}>
          Level: {level}
        </Badge>
      </div>
      <Button
        className="d-none d-md-block"
        variant="primary"
        style={{ margin: "1rem" }}
        onClick={handlePlayerClick}
      >
        View Profile
      </Button>
    </Card>
  );
};

const Team = () => {
  const location = useLocation();
  const searchParams = new URLSearchParams(location.search);
  const id = searchParams.get("id");

  const teamsMap = new Map<string, Team>();

  matchesList.forEach((match) => {
    teamsMap.set(match.teams.faction1.faction_id, match.teams.faction1);
    teamsMap.set(match.teams.faction2.faction_id, match.teams.faction2);
  });

  const uniqueTeams = Array.from(teamsMap.values());
  const team = uniqueTeams.find((team) => team.faction_id === id);

  if (!team) {
    return <div>Team not found</div>;
  }

  return (
    <Container style={{ marginTop: "0.5rem", padding: "0 1rem" }}>
      <h1 className="text-center">Team Details</h1>
      <div className="d-flex justify-content-center align-items-center">
        <Image
          src={team.avatar}
          alt={team.name}
          style={{ height: "5rem", marginRight: "1rem" }}
          fluid
        />
        <h1 className="text-center" style={{ fontSize: "5rem" }}>
          {team.name}
        </h1>
      </div>

      <Container style={{ marginTop: "1rem" }}>
        <div className="d-flex justify-content-center">
          {team.roster.map((player) => (
            <Player
              nickname={player.nickname}
              avatar={player.avatar}
              level={player.game_skill_level}
            />
          ))}
        </div>
      </Container>
    </Container>
  );
};

export default Team;
