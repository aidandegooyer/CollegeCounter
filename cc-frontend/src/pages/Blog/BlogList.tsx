import { useEffect, useState } from "react";
import { Container, Spinner } from "react-bootstrap";
import client from "../../sanityClient";
import BlogPost from "./BlogPost";
import { SanityPost } from "./BlogTypes";

const BlogList = () => {
  const [posts, setPosts] = useState<SanityPost[]>([]);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(1);
  const offset = (page - 1) * 5;
  const limit = 5;

  useEffect(() => {
    setLoading(true);
    client
      .fetch<SanityPost[]>(
        `*[_type == "post"] | order(_createdAt desc) [${offset}...${
          offset + limit
        }]`
      )
      .then((data) => {
        setPosts(data);
        setLoading(false);
      })
      .catch((err) => {
        console.error("Error fetching blog posts:", err);
        setLoading(false);
      });
  }, []);

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

  return (
    <Container>
      <h1>News</h1>
      {posts
        .sort(
          (a, b) =>
            new Date(b.publishedAt).getTime() -
            new Date(a.publishedAt).getTime()
        )
        .map((post, key) => (
          <BlogPost post={post} key={key} small={key !== 0} medium={key == 0} />
        ))}
    </Container>
  );
};

export default BlogList;
