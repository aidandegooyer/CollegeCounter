import { useEffect, useState } from "react";
import { Card, Container, Spinner } from "react-bootstrap";
import client from "../../sanityClient";
import imageUrlBuilder from "@sanity/image-url";
import { PortableText, PortableTextComponents } from "@portabletext/react";

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

// ✅ Fix: Correctly define the PortableText components
const portableTextComponents: PortableTextComponents = {
  types: {
    image: ({ value }: { value: SanityImage }) => (
      <img
        src={urlFor(value).width(600).url()}
        alt="Sanity Image"
        style={{ maxWidth: "100%", height: "auto", borderRadius: "8px" }}
      />
    ),
  },
  marks: {
    strong: ({ children }) => <strong>{children}</strong>,
    em: ({ children }) => <em>{children}</em>,
    link: ({ value, children }) => (
      <a href={value.href} target="_blank" rel="noopener noreferrer">
        {children}
      </a>
    ),
  },
  block: {
    normal: ({ children }) => <p>{children}</p>,
    h1: ({ children }) => <h1>{children}</h1>,
    h2: ({ children }) => <h2>{children}</h2>,
    blockquote: ({ children }) => (
      <blockquote style={{ borderLeft: "4px solid #ccc", paddingLeft: "10px" }}>
        {children}
      </blockquote>
    ),
  },
  list: {
    bullet: ({ children }) => <ul>{children}</ul>,
    number: ({ children }) => <ol>{children}</ol>,
  },
  listItem: {
    bullet: ({ children }) => <li>{children}</li>,
    number: ({ children }) => <li>{children}</li>,
  },
};

const BlogPosts = () => {
  const [posts, setPosts] = useState<SanityPost[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    client
      .fetch<SanityPost[]>('*[_type == "post"]')
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
          <Card className="mb-4" key={key}>
            {post.image && (
              <Card.Img
                variant="top"
                src={urlFor(post.image).width(540).height(300).url()}
                alt={post.title}
                style={{ maxHeight: "300px", objectFit: "cover" }}
              />
            )}
            <Card.Body>
              <Card.Title style={{ fontSize: "2rem" }}>{post.title}</Card.Title>
              <Card.Subtitle className="mb-2 text-muted">
                {new Date(post.publishedAt).toLocaleDateString("en-US", {
                  year: "numeric",
                  month: "long",
                  day: "numeric",
                })}{" "}
                |{" "}
                {post.authorLink ? (
                  <a href={post.authorLink}>{post.author}</a>
                ) : (
                  post.author
                )}
              </Card.Subtitle>

              <PortableText
                value={post.body}
                components={portableTextComponents}
              />
            </Card.Body>
          </Card>
        ))}
    </Container>
  );
};

export default BlogPosts;
