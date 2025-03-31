import { Container, Row, Col } from "react-bootstrap";

const Footer = () => {
  return (
    <footer
      style={{
        marginTop: "2rem",
        padding: "1rem 0",
        textAlign: "center",
      }}
    >
      <Container>
        <hr />
        <Row>
          <span>
            <a href="https://x.com/College_Counter">
              <i
                className="mx-2 bi bi-twitter-x"
                style={{ fontSize: "1.5rem", color: "var(--bs-gray)" }}
              ></i>
            </a>
            <a href="https://discord.gg/yzNMNDFTT6">
              <i
                className="mx-2 bi bi-discord"
                style={{ fontSize: "1.5rem", color: "var(--bs-gray)" }}
              ></i>
            </a>
          </span>
        </Row>
        <Row>
          <Col>
            <span style={{ fontSize: "0.8rem", color: "var(--bs-gray)" }}>
              Created by <a href="https://x.com/aidan_xi">aidanxi</a> and{" "}
              <a href="https://x.com/senshi_cs">senshi</a>{" "}
              <i className="bi bi-emoji-smile-fill"></i>
            </span>
          </Col>
        </Row>
        <Row>
          <span style={{ fontSize: "0.8rem", color: "var(--bs-gray)" }}>
            ©2025 Station XI LLC.
          </span>
        </Row>
      </Container>
    </footer>
  );
};

export default Footer;
