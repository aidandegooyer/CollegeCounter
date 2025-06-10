import { Container, Spinner } from "react-bootstrap";
import BlogPost from "./BlogPost";
import client from "../../sanityClient";
import { SanityPost } from "./BlogTypes";
import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";

const BlogPage = () => {
  const slug = useParams();
  const [post, setPost] = useState<SanityPost>();
  const [loading, setLoading] = useState(true);
  console.log(slug);

  useEffect(() => {
    fetchPost();
  }, []);
  function fetchPost() {
    client
      .fetch<SanityPost>(
        `*[_type == "post" && slug.current == "${slug.slug}"][0]`
      )
      .then((data) => {
        setPost(data);
        setLoading(false);
      })
      .catch((err) => {
        console.error("Error fetching blog posts:", err);
        setLoading(false);
      });
  }

  if (loading)
    return (
      <div
        style={{
          display: "flex",
          justifyContent: "center",
          alignItems: "center",
          height: "100vh",
        }}
      >
        <Spinner animation="border" />
      </div>
    );

  if (!post) {
    return (
      <Container
        style={{
          display: "flex",
          justifyContent: "center",
          alignItems: "center",
          height: "100vh",
        }}
      >
        <h1>Post not found</h1>
      </Container>
    );
  }
  return (
    <Container
      style={{ marginTop: "0.5rem", maxWidth: "800px", padding: "0 1rem" }}
    >
      <BlogPost post={post} full />
    </Container>
  );
};

export default BlogPage;
