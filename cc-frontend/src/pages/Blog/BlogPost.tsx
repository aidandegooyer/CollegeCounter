import { Card } from "react-bootstrap";
import client from "../../sanityClient";
import imageUrlBuilder from "@sanity/image-url";
import { PortableText, PortableTextComponents } from "@portabletext/react";
import { SanityImage, SanityPost } from "./BlogTypes";
import { Link } from "react-router";

const builder = imageUrlBuilder(client);

function urlFor(source: any) {
  return builder.image(source);
}

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

interface BlogPostProps {
  post: SanityPost;
  full?: boolean;
  medium?: boolean;
  small?: boolean;
}

const BlogPost: React.FC<BlogPostProps> = ({ post, medium, small }) => {
  if (small) {
    return (
      <Card className="mb-4">
        <Card.Body>
          <Link to={`/blog/${post.slug.current}`}>
            <Card.Title
              style={{ fontSize: "1.5rem", color: "var(--bs-body-color)" }}
            >
              {post.title}
            </Card.Title>
          </Link>
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
        </Card.Body>
      </Card>
    );
  }
  if (medium) {
    return (
      <Card className="mb-4">
        {post.image && (
          <Card.Img
            variant="top"
            src={urlFor(post.image).width(540).height(300).url()}
            alt={post.title}
            style={{ maxHeight: "300px", objectFit: "cover" }}
          />
        )}
        <Card.Body>
          <Link to={`/blog/${post.slug.current}`}>
            <Card.Title
              style={{ fontSize: "2rem", color: "var(--bs-body-color)" }}
            >
              {post.title}
            </Card.Title>
          </Link>
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
        </Card.Body>
      </Card>
    );
  }

  return (
    <Card className="mb-4">
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

        <PortableText value={post.body} components={portableTextComponents} />
      </Card.Body>
    </Card>
  );
};

export default BlogPost;
