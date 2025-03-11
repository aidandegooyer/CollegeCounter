import { Container } from "react-bootstrap";
import BlogList from "./BlogList";

const Blog = () => {
  return (
    <Container
      style={{ marginTop: "0.5rem", maxWidth: "1000px", padding: "0 1rem" }}
    >
      <BlogList />
    </Container>
  );
};

export default Blog;
