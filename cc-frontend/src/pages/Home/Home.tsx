import { Col, Container, Row, Image } from "react-bootstrap";
import Ranking from "./Ranking";
import Matches from "./Matches";

import logo from "../../assets/0.1x/C Logo@0.1x.png";
import Blog from "./Blog";

const Home = () => {
  return (
    <Container
      style={{ marginTop: "0.5rem", maxWidth: "1300px", padding: "0 1rem" }}
    >
      <Container>
        <Image src={logo} alt="logo" style={{ width: "75px" }} />
      </Container>

      <Row style={{ marginTop: "2rem" }}>
        <Col lg={3} md={4} className="d-none d-md-block">
          <Ranking />
        </Col>
        <Col lg={6} md={8}>
          <Blog />
        </Col>
        <Col lg={3} className="d-none d-lg-block">
          <Matches />
        </Col>
      </Row>
    </Container>
  );
};

export default Home;
