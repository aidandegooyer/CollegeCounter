import { useState, useEffect } from "react";
import { useParams, Link } from "react-router";
import client from "@/services/sanity-client";
import { formatDistance } from "date-fns";
import { Spinner } from "@/components/ui/shadcn-io/spinner";
import { ChevronLeft, ExternalLink } from "lucide-react";
import { PortableText } from "@portabletext/react";
import type { PortableTextComponents } from "@portabletext/react";

interface SanityImage {
  _type: "image";
  asset: {
    _type: "reference";
    _ref: string;
    url: string;
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
  mainImage?: SanityImage;
  imageUrl?: string;
  author?: string;
  authorLink?: string;
  publishedAt: string;
}

function Article() {
  const { slug } = useParams<{ slug: string }>();
  const [post, setPost] = useState<SanityPost | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchPost = async () => {
      if (!slug) {
        setError("Article not found");
        setLoading(false);
        return;
      }

      try {
        setLoading(true);
        // Query for the specific post by slug
        const query = `*[_type == "post" && slug.current == $slug][0]{
          _id,
          title,
          slug,
          body[]{
    ...,
    _type == "image" => {
      ...,
      "url": asset->url
    }
},
          "imageUrl": image.asset->url,
          author,
          authorLink,
          publishedAt
        }`;

        const result = await client.fetch(query, { slug });

        if (!result) {
          setError("Article not found");
        } else {
          setPost(result);
          // Set the document title to the article title
          document.title = `${result.title} - College Counter News`;
        }
      } catch (err) {
        console.error("Error fetching post:", err);
        setError("Failed to load article");
      } finally {
        setLoading(false);
      }
    };

    fetchPost();
  }, [slug]);

  if (loading) {
    return (
      <div className="bg-background flex h-screen items-center justify-center">
        <Spinner className="text-primary h-12 w-12" />
      </div>
    );
  }

  if (error || !post) {
    return (
      <div className="container mx-auto max-w-3xl px-4 py-12">
        <div className="mb-8">
          <Link
            to="/news"
            className="text-primary flex items-center transition-colors hover:underline"
          >
            <ChevronLeft className="mr-1 h-4 w-4" />
            Back to News
          </Link>
        </div>
        <div className="border-destructive/20 bg-destructive/10 rounded-lg border p-8 text-center">
          <h1 className="text-destructive mb-4 text-2xl font-bold">{error}</h1>
          <p className="text-destructive/80">
            The article you're looking for couldn't be found.
          </p>
          <Link
            to="/news"
            className="bg-primary text-primary-foreground hover:bg-primary/90 mt-6 inline-block rounded-md px-4 py-2 transition-colors"
          >
            Browse all news articles
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="container mx-auto max-w-4xl px-4 py-2">
      <div className="mb-8">
        <Link
          to="/news"
          className="text-primary flex items-center transition-colors hover:underline"
        >
          <ChevronLeft className="mr-1 h-4 w-4" />
          Back to News
        </Link>
      </div>

      <article className="text-foreground border-border overflow-hidden rounded-xl border shadow-md">
        {post.imageUrl && (
          <div className="relative h-[400px] w-full">
            <img
              src={post.imageUrl}
              alt={post.title}
              className="h-full w-full object-cover"
            />
          </div>
        )}

        <div className="p-8">
          <h1 className="text-foreground mb-4 text-4xl font-bold md:text-5xl lg:text-6xl">
            {post.title}
          </h1>

          <div className="text-muted-foreground mb-8 flex flex-wrap items-center justify-between text-sm">
            <span className="font-medium">
              {post.author || "College Counter Staff"}
            </span>
            <span>
              {formatDistance(new Date(post.publishedAt), new Date(), {
                addSuffix: true,
              })}
            </span>
          </div>

          <div className="prose prose-lg text-foreground max-w-none">
            <PortableText
              value={post.body}
              components={portableTextComponents}
            />
          </div>
        </div>
      </article>
    </div>
  );
}

// Custom components for PortableText rendering
const portableTextComponents: PortableTextComponents = {
  block: {
    // You can edit the styling here for h1 tags
    normal: ({ children }) => (
      <p className="text-foreground mb-6">{children}</p>
    ),
    h1: ({ children }) => (
      <h1 className="text-foreground mb-6 mt-8 text-4xl">{children}</h1>
    ),
    h2: ({ children }) => (
      <h2 className="text-foreground mb-4 mt-8 text-3xl font-bold">
        {children}
      </h2>
    ),
    h3: ({ children }) => (
      <h3 className="text-foreground mb-4 mt-6 text-2xl font-bold">
        {children}
      </h3>
    ),
    h4: ({ children }) => (
      <h4 className="text-foreground mb-4 mt-6 text-xl font-bold">
        {children}
      </h4>
    ),
    blockquote: ({ children }) => (
      <blockquote className="border-primary bg-muted/30 text-foreground my-6 border-l-4 py-2 pl-4">
        {children}
      </blockquote>
    ),
  },
  marks: {
    link: ({ children, value }) => {
      const rel = !value.href.startsWith("/")
        ? "noreferrer noopener"
        : undefined;
      const target = !value.href.startsWith("/") ? "_blank" : undefined;

      return (
        <a
          href={value.href}
          rel={rel}
          target={target}
          className="text-primary mr-0.5 inline-flex items-center font-medium hover:underline"
        >
          {children}
          {target === "_blank" && (
            <ExternalLink className="ml-1 inline h-3 w-3" />
          )}
        </a>
      );
    },
    strong: ({ children }) => (
      <strong className="text-foreground font-bold">{children}</strong>
    ),
    em: ({ children }) => (
      <em className="text-foreground italic">{children}</em>
    ),
    code: ({ children }) => (
      <code className="bg-muted rounded px-1 py-0.5 font-mono text-sm">
        {children}
      </code>
    ),
  },
  list: {
    bullet: ({ children }) => (
      <ul className="mb-6 list-disc space-y-2 pl-6">{children}</ul>
    ),
    number: ({ children }) => (
      <ol className="mb-6 list-decimal space-y-2 pl-6">{children}</ol>
    ),
  },
  listItem: {
    bullet: ({ children }) => <li className="text-foreground">{children}</li>,
    number: ({ children }) => <li className="text-foreground">{children}</li>,
  },
  types: {
    image: ({ value }) => {
      if (!value?.asset?._ref) {
        return null;
      }
      const imageUrl = value.url;
      const caption = value.caption;
      return (
        <div>
          <img
            src={imageUrl}
            alt={value.alt || "Article Image"}
            className="mt-6 w-full rounded-lg"
          />
          <div className="border-primary bg-muted/30 text-foreground mb-6 mt-2 border-t-4 py-2 pl-4">
            {caption}
          </div>
        </div>
      );
    },
  },
};

export default Article;
