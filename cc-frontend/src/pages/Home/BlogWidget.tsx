import { useEffect, useState } from "react";
import { Container, Spinner } from "react-bootstrap";
import BlogPost from "../Blog/BlogPost";
import client from "../../sanityClient";
import imageUrlBuilder from "@sanity/image-url";

// Configure Sanity image builder
const builder = imageUrlBuilder(client);

function urlFor(source: any) {
  return builder.image(source);
}

// Define TypeScript types for Sanity Blog Posts
interface SanityImage {
  _type: "image";
  asset: {
    _type: "reference";
    _ref: string;
  };
}

interface PortableTextBlock {
  _type: "block";
  _key: string;
  style?: string;
  markDefs?: { _key: string; _type: string; href?: string }[];
  children: { _type: "span"; text: string; _key: string; marks?: string[] }[];
}

interface SanityPost {
  _id: string;
  title: string;
  slug: { _type: "slug"; current: string };
  body: PortableTextBlock[];
  image?: SanityImage;
  author?: string;
  authorLink?: string;
  publishedAt: string;
}

const BlogWidget = () => {
  const [posts, setPosts] = useState<SanityPost[]>([]);
  const [loading, setLoading] = useState(true);
  const offset = 0;
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

export default BlogWidget;
