import { Card, Badge, Button } from "react-bootstrap";
import { Player } from "../../types";
import errorImage from "../../assets/error-profile-pic.png";

interface PlayerCardProps {
  player: Player;
  leader: boolean;
}

const PlayerCard: React.FC<PlayerCardProps> = ({ player, leader }) => {
  const handlePlayerClick = () => {
    // open new tab with player profile
    window.open(`https://www.faceit.com/en/players/${player.nickname}`);
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
    <>
      {player.avatar ? (
        <img
          src={player.avatar}
          style={{ width: "200px" }}
          onError={(e) => {
            e.currentTarget.onerror = null;
            e.currentTarget.src = errorImage;
          }}
        />
      ) : (
        <img src={errorImage} style={{ width: "200px" }} />
      )}

      <Card style={{ width: "200px" }}>
        <Card.Title
          className="text-center"
          style={{ fontSize: "1.5rem", marginTop: "1rem" }}
        >
          {leader ? (
            <i
              className="bi bi-star"
              style={{ fontSize: "1rem", color: "gold", marginRight: "0.5rem" }}
            />
          ) : (
            ""
          )}
          {player.nickname}
        </Card.Title>
        <div className="d-flex justify-content-center">
          <Badge
            bg={getLevelColor(player.skill_level)}
            style={{ width: "150px" }}
          >
            Level: {player.skill_level} (ELO: {player.elo})
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
    </>
  );
};

export default PlayerCard;
