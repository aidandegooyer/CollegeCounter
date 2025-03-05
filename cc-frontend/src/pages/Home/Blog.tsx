import React from "react";
import { Card, Container, Row, Col, Image } from "react-bootstrap";
import logo from "../../assets/1x/C Logo.png";

const Blog: React.FC = () => {
  return (
    <Container>
      <h3 style={{ fontSize: "1.5rem" }}>Blog</h3>
      <Col>
        <Row md={12} className="mb-4">
          <Card>
            <Card.Body>
              <Card.Title>Blog Coming Soon</Card.Title>
              <Card.Subtitle className="mb-2 text-muted">
                Author - Date
              </Card.Subtitle>
              <Image
                src={logo}
                alt="blog post"
                fluid
                style={{ width: "100%", height: "300px", objectFit: "cover" }}
              />
              <Card.Text>soon (tm)</Card.Text>
            </Card.Body>
          </Card>
        </Row>
      </Col>
    </Container>
  );
};

export default Blog;
