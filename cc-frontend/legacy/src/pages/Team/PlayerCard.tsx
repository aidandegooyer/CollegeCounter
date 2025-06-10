import { Card, Badge } from "react-bootstrap";
import { Player } from "../../types";
import errorImage from "../../assets/error-profile-pic.png";
import { Link } from "react-router-dom";

interface PlayerCardProps {
  player: Player;
  leader: boolean;
  image?: boolean;
}

const PlayerCard: React.FC<PlayerCardProps> = ({ player, leader, image }) => {
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
      {image && (
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
        </>
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
          <Link
            to={`/player?id=${player.player_id}`}
            style={{ color: "var(--bs-body-color)" }}
          >
            {player.nickname}
          </Link>
        </Card.Title>
        <div className="d-flex justify-content-center">
          <Badge
            bg={getLevelColor(player.skill_level)}
            style={{ width: "150px", marginBottom: "1rem" }}
          >
            Level: {player.skill_level} (ELO: {player.elo})
          </Badge>
        </div>
      </Card>
    </>
  );
};

export default PlayerCard;
