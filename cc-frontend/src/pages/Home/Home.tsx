import { Col, Container, Row, Alert } from "react-bootstrap";
import RankingWidget from "./RankingWidget";
import MatchesWidget from "./MatchesWidget";
import BlogWidget from "./BlogWidget";
import { useEffect } from "react";
import { useState } from "react";
const apiBaseUrl =
  import.meta.env.VITE_API_BASE_URL || "https://api.collegecounter.org";

const Home = () => {
  document.title = "College Counter";

  const [alertText, setAlertText] = useState<string | null>(null);

  useEffect(() => {
    const fetchAlertText = async () => {
      try {
        const response = await fetch(`${apiBaseUrl}/alert`);
        const data = await response.text();
        setAlertText(data);
      } catch (error) {
        console.error("Error fetching alert text:", error);
      }
    };

    fetchAlertText();
  }, []);

  return (
    <Container
      style={{ marginTop: "0.5rem", maxWidth: "1500px", padding: "0 1rem" }}
    >
      {alertText ? (
        <Alert variant="primary" dismissible>
          {alertText && <div dangerouslySetInnerHTML={{ __html: alertText }} />}
        </Alert>
      ) : null}
      <Row style={{ marginTop: "2rem" }}>
        <Col lg={3} md={4} className="d-none d-md-block">
          <RankingWidget />
        </Col>
        <Col lg={6} md={8}>
          <BlogWidget />
        </Col>
        <Col lg={3} className="d-none d-lg-block">
          <MatchesWidget />
        </Col>
      </Row>
    </Container>
  );
};

export default Home;
