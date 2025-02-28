import {
  Container,
  Row,
  Col,
  Card,
  Badge,
  Button,
  Image,
} from "react-bootstrap";
import matchesList from "../../../../cc-ranking/.dev/upcoming.json";
import { useEffect, useState } from "react";
import { format } from "date-fns";

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

interface Match {
  match_id: string;
  version: number;
  game: string;
  region: string;
  competition_id: string;
  competition_type: string;
  competition_name: string;
  organizer_id: string;
  teams: {
    faction1: Team;
    faction2: Team;
  };
  scheduled_at: number;
  status: string;
  faceit_url: string;
}

interface MatchProps {
  match: Match;
  today?: boolean;
  thisweek?: boolean;
}

const Match = ({ match, today, thisweek }: MatchProps) => {
  const [timeLeft, setTimeLeft] = useState<string>("");

  function openMatchPage(match: Match) {
    const url = match.faceit_url.replace("{lang}", "en");
    window.open(url, "_blank")?.focus();
  }

  if (today) {
    useEffect(() => {
      const interval = setInterval(() => {
        const now = new Date().getTime();
        const distance = match.scheduled_at * 1000 - now;

        if (distance < 0) {
          clearInterval(interval);
          setTimeLeft("Match started");
        } else {
          const hours = Math.floor(
            (distance % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60)
          );
          const minutes = Math.floor(
            (distance % (1000 * 60 * 60)) / (1000 * 60)
          );
          setTimeLeft(`${hours}h ${minutes}m`);
        }
      }, 5000);

      return () => clearInterval(interval);
    }, [match.scheduled_at]);
    return (
      <Card style={{ marginBottom: "1rem" }}>
        <Row style={{ padding: "1rem" }}>
          <Col>
            <Row style={{ marginBottom: "1rem" }}>
              <div style={{ display: "flex", alignItems: "center" }}>
                <img
                  src={match.teams.faction1.avatar}
                  style={{ width: "50px", height: "50px" }}
                ></img>
                <h3 style={{ marginLeft: "10px", marginRight: "10px" }}>
                  {match.teams.faction1.name}
                </h3>
                <Badge bg="info">#23</Badge>
              </div>
            </Row>
            <Row>
              <div style={{ display: "flex", alignItems: "center" }}>
                <img
                  src={match.teams.faction2.avatar}
                  style={{ width: "50px", height: "50px" }}
                ></img>
                <h3 style={{ marginLeft: "10px", marginRight: "10px" }}>
                  {match.teams.faction2.name}
                </h3>
                <Badge bg="info">#23</Badge>
              </div>
            </Row>
          </Col>
          <Col style={{ marginRight: "1rem" }} className="text-end">
            <Row className="justify-content-end">
              <h3>{format(new Date(match.scheduled_at * 1000), "h:mm aaa")}</h3>
            </Row>
            <Row className="justify-content-end">
              <h3>{timeLeft}</h3>
            </Row>
            <Row className="justify-content-end">
              <Badge bg="secondary" style={{ maxWidth: "50px" }}>
                NECC
              </Badge>
            </Row>
          </Col>
          <Button
            variant="primary"
            style={{ marginTop: "20px" }}
            onClick={() => openMatchPage(match)}
          >
            Details
          </Button>
        </Row>
      </Card>
    );
  }

  if (thisweek) {
    return (
      <Card style={{ marginBottom: "1rem" }}>
        <Row style={{ padding: "1rem" }}>
          <Col>
            <Row style={{ marginBottom: "1rem" }}>
              <div style={{ display: "flex", alignItems: "center" }}>
                <img
                  src={match.teams.faction1.avatar}
                  style={{ width: "50px", height: "50px" }}
                ></img>
                <h4 style={{ marginLeft: "10px", marginRight: "10px" }}>
                  {match.teams.faction1.name}
                </h4>
                <Badge bg="info">#23</Badge>
              </div>
            </Row>
            <Row>
              <div style={{ display: "flex", alignItems: "center" }}>
                <img
                  src={match.teams.faction2.avatar}
                  style={{ width: "50px", height: "50px" }}
                ></img>
                <h4 style={{ marginLeft: "10px", marginRight: "10px" }}>
                  {match.teams.faction2.name}
                </h4>
                <Badge bg="info">#23</Badge>
              </div>
            </Row>
          </Col>
          <Col style={{ marginRight: "1rem" }}>
            <Row className="justify-content-end">
              {format(new Date(match.scheduled_at * 1000), "MMM do, h:mm aaa")}
            </Row>
            <Row className="justify-content-end mt-1">
              <Badge bg="secondary" style={{ maxWidth: "50px" }}>
                NECC
              </Badge>
            </Row>
            <Row className="justify-content-end mt-1">
              <Button
                variant="primary"
                style={{ maxWidth: "100px", height: "40px" }}
                onClick={() => openMatchPage(match)}
              >
                Details <i className="bi bi-arrow-right"></i>
              </Button>
            </Row>
          </Col>
        </Row>
      </Card>
    );
  }

  return (
    <Card style={{ marginBottom: "1rem", maxWidth: "400px" }}>
      <Row>
        <Col md={8}>
          <Row>
            <div style={{ display: "flex", alignItems: "center" }}>
              <img
                src={match.teams.faction1.avatar}
                style={{ width: "30px", height: "30px" }}
              ></img>
              <h6 style={{ marginLeft: "10px", marginRight: "10px" }}>
                {match.teams.faction1.name}
              </h6>
              <Badge bg="info">#23</Badge>
            </div>
          </Row>
          <Row>
            <div style={{ display: "flex", alignItems: "center" }}>
              <img
                src={match.teams.faction2.avatar}
                style={{ width: "30px", height: "30px" }}
              ></img>
              <h6 style={{ marginLeft: "10px", marginRight: "10px" }}>
                {match.teams.faction2.name}
              </h6>
              <Badge bg="info">#23</Badge>
            </div>
          </Row>
        </Col>
        <Col md={4} className="text-end">
          <Row className="justify-content-end" style={{ marginRight: "1rem" }}>
            {format(new Date(match.scheduled_at * 1000), "MMM do")}
          </Row>
          <Row className="justify-content-end" style={{ marginRight: "1rem" }}>
            {format(new Date(match.scheduled_at * 1000), "h:mm aaa")}
          </Row>
        </Col>
      </Row>
    </Card>
  );
};

const Matches = () => {
  const [todayMatches, setTodayMatches] = useState<Match[]>([]);
  const [thisWeekMatches, setThisWeekMatches] = useState<Match[]>([]);
  const [otherMatches, setOtherMatches] = useState<Match[]>([]);

  useEffect(() => {
    const today = new Date();
    const endOfToday = new Date(today);
    endOfToday.setHours(23, 59, 59, 999);

    const endOfWeek = new Date(today);
    endOfWeek.setDate(today.getDate() + (7 - today.getDay()));
    endOfWeek.setHours(23, 59, 59, 999);

    const todayMatchesTemp: Match[] = [];
    const thisWeekMatchesTemp: Match[] = [];
    const otherMatchesTemp: Match[] = [];

    matchesList.forEach((match) => {
      const matchDate = new Date(match.scheduled_at * 1000);
      if (matchDate <= endOfToday) {
        todayMatchesTemp.push(match);
      } else if (matchDate <= endOfWeek) {
        thisWeekMatchesTemp.push(match);
      } else {
        otherMatchesTemp.push(match);
      }
    });

    todayMatchesTemp.sort((a, b) => a.scheduled_at - b.scheduled_at);
    thisWeekMatchesTemp.sort((a, b) => a.scheduled_at - b.scheduled_at);
    otherMatchesTemp.sort((a, b) => a.scheduled_at - b.scheduled_at);

    setTodayMatches(todayMatchesTemp);
    setThisWeekMatches(thisWeekMatchesTemp);
    setOtherMatches(otherMatchesTemp);
  }, []);

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
              <Match match={match} />
            </Col>
          ))}
        </Row>
      );
    }

    return matches.map((match: Match) => (
      <Match
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
        <h1>Upcoming Matches</h1>
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
