import { Col, Container, Row, Alert } from "react-bootstrap";
import RankingWidget from "./RankingWidget";
import MatchesWidget from "./MatchesWidget";
import Blog from "./Blog";
import { useEffect } from "react";

const Home = () => {
  useEffect(() => {
    document.title = "College Counter";
  }, []);

  return (
    <Container
      style={{ marginTop: "0.5rem", maxWidth: "1500px", padding: "0 1rem" }}
    >
      <Alert variant="primary">
        Welcome to College Counter! This is version 0.0.1 pre alpha beta test :)
        <br />
        <br />A lot of stuff doesnt work and is broken but if you are a team
        captain please email us your headshots at:{" "}
        <strong>collegiatecounter@gmail.com</strong>
        <br />
        <br />
        Please also go join our{" "}
        <a href="https://discord.gg/yzNMNDFTT6">Discord</a> and follow us on{" "}
        <a href="https://x.com/College_Counter">Twitter</a>
      </Alert>
      <Row style={{ marginTop: "2rem" }}>
        <Col lg={4} md={5} className="d-none d-md-block">
          <RankingWidget />
        </Col>
        <Col lg={5} md={7}>
          <Blog />
        </Col>
        <Col lg={3} className="d-none d-lg-block">
          <MatchesWidget />
        </Col>
      </Row>
      <footer
        style={{
          marginTop: "2rem",
          padding: "1rem 0",
          textAlign: "center",
        }}
      >
        <Container>
          <Row>
            <Col>
              <span style={{ fontSize: "0.8rem", color: "var(--bs-gray)" }}>
                Created by <a href="https://x.com/aidan_xi">aidanxi</a> and{" "}
                <a href="https://x.com/senshi_cs">senshi</a>{" "}
                <i className="bi bi-emoji-smile-fill"></i>
              </span>
            </Col>
          </Row>
        </Container>
      </footer>{" "}
    </Container>
  );
};

export default Home;
