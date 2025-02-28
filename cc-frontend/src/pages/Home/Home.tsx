import { Col, Container, Row } from "react-bootstrap";
import RankingWidget from "./RankingWidget";
import MatchesWidget from "./MatchesWidget";
import Blog from "./Blog";

const Home = () => {
  return (
    <Container
      style={{ marginTop: "0.5rem", maxWidth: "1300px", padding: "0 1rem" }}
    >
      <Row style={{ marginTop: "2rem" }}>
        <Col
          lg={3}
          md={5}
          className="d-none d-md-block"
          style={{ minWidth: "300px" }}
        >
          <RankingWidget />
        </Col>
        <Col lg={6} md={7}>
          <Blog />
        </Col>
        <Col lg={3} className="d-none d-lg-block">
          <MatchesWidget />
        </Col>
      </Row>
    </Container>
  );
};

export default Home;
