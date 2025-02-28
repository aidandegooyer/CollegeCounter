import React from "react";
import { Card, Container, Row, Col } from "react-bootstrap";

const Blog: React.FC = () => {
  const blogPosts = [
    {
      title: "First Blog Post",
      content: "This is the content of the first blog post.",
      author: "Author 1",
      date: "2023-10-01",
    },
    {
      title: "Second Blog Post",
      content: "This is the content of the second blog post.",
      author: "Author 2",
      date: "2023-10-02",
    },
    {
      title: "Third Blog Post",
      content: "This is the content of the third blog post.",
      author: "Author 3",
      date: "2023-10-03",
    },
    {
      title: "Fourth Blog Post",
      content: "This is the content of the fourth blog post.",
      author: "Author 4",
      date: "2023-10-04",
    },
    {
      title: "Fifth Blog Post",
      content: "This is the content of the fifth blog post.",
      author: "Author 5",
      date: "2023-10-05",
    },
  ];

  return (
    <Container>
      <h3 style={{ fontSize: "1.5rem" }}>Blog</h3>
      <Col>
        {blogPosts.map((post, index) => (
          <Row key={index} md={12} className="mb-4">
            <Card>
              <Card.Body>
                <Card.Title>{post.title}</Card.Title>
                <Card.Subtitle className="mb-2 text-muted">
                  {post.author} - {post.date}
                </Card.Subtitle>
                <img src="holder.js/100px180" alt="blog post" />
                <Card.Text>{post.content}</Card.Text>
              </Card.Body>
            </Card>
          </Row>
        ))}
      </Col>
    </Container>
  );
};

export default Blog;
