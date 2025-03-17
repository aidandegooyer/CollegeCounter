import React from "react";
import { Container, Row, Col, Button } from "react-bootstrap";
import { Link } from "react-router-dom";

const NotFoundPage: React.FC = () => {
  return (
    <Container
      className="d-flex justify-content-center align-items-center"
      style={{ marginTop: "50px", height: "calc(80vh - 200px)" }}
    >
      <Row>
        <Col className="text-center">
          <h1>404</h1>
          <h2>Page Not Found</h2>
          <p>Sorry, the page you are looking for does not exist.</p>
          <Link to="/">
            <Button variant="primary">Go to Home</Button>
          </Link>
        </Col>
      </Row>
    </Container>
  );
};

export default NotFoundPage;
