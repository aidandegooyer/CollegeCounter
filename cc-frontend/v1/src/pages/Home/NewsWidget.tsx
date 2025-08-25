import { useState, useEffect } from "react";
import { ChevronRight } from "lucide-react";
import logo from "@/assets/0.5x/C Logo@0.5x.png";
import { NavLink } from "react-router";
import client from "@/services/sanity-client";
import { Spinner } from "@/components/ui/shadcn-io/spinner";
import { formatDistanceToNow } from "date-fns";
import { useNavigate } from "react-router";

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
  body?: PortableTextBlock[];
  excerpt?: string;
  imageUrl?: string;
  author?: string;
  authorLink?: string;
  publishedAt: string;
}

function NewsWidget() {
  const [posts, setPosts] = useState<SanityPost[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchPosts = async () => {
      try {
        setLoading(true);
        // Query for posts, ordered by publishedAt date, limited to 3
        const query = `*[_type == "post"] | order(publishedAt desc)[0...8]{
          _id,
          title,
          slug,
          "excerpt": array::join(string::split(pt::text(body), "")[0...150], ""),
          publishedAt,
          "imageUrl": image.asset->url,
          author,
          authorLink
        }`;

        const result = await client.fetch(query);
        setPosts(result);
      } catch (err) {
        console.error("Error fetching posts:", err);
        setError("Failed to load news posts");
      } finally {
        setLoading(false);
      }
    };

    fetchPosts();
  }, []);

  // If there are no posts but we're not loading, render a placeholder
  const renderContent = () => {
    if (loading) {
      return (
        <div className="flex h-64 items-center justify-center">
          <Spinner className="h-8 w-8" />
        </div>
      );
    }

    if (error) {
      return <div className="mt-4 text-center text-red-500">{error}</div>;
    }

    if (posts.length === 0) {
      return (
        <div className="text-muted-foreground mt-4 text-center">
          No news posts available
        </div>
      );
    }

    return (
      <ul className="mt-2 space-y-4">
        {posts.length > 0 && <FeaturedNews post={posts[0]} />}
        {posts.slice(1).map((post) => (
          <NewsItem key={post._id} post={post} />
        ))}
      </ul>
    );
  };

  return (
    <div className="news-widget">
      <NavLink
        to="/news"
        className="group flex cursor-pointer items-center justify-between"
      >
        <h2>News</h2>
        <ChevronRight className="text-muted-foreground mr-2 h-6 w-6 transition-all group-hover:mr-0" />
      </NavLink>
      <hr />
      {renderContent()}
    </div>
  );
}

export default NewsWidget;

function FeaturedNews({ post }: { post: SanityPost }) {
  const navigate = useNavigate();
  const handleClick = () => {
    navigate(`/news/${post.slug.current}`);
  };

  return (
    <div
      className="featured-news cursor-pointer rounded-xl border-2 transition-colors hover:border-blue-400"
      onClick={handleClick}
    >
      <img
        src={post.imageUrl || logo}
        className="h-64 w-full rounded-xl object-cover"
        alt={post.title}
      />
      <div className="p-4 pt-2">
        <h2 className="text-lg font-semibold">{post.title}</h2>

        <div className="mt-2 flex justify-between">
          <span className="text-foreground bg-secondary rounded px-1 py-0.5 text-sm">
            {post.author || "College Counter Staff"}
          </span>
          <span className="text-muted-foreground text-sm">
            {formatDistanceToNow(new Date(post.publishedAt), {
              addSuffix: true,
            })}
          </span>
        </div>
      </div>
    </div>
  );
}

function NewsItem({ post }: { post: SanityPost }) {
  const navigate = useNavigate();
  const handleClick = () => {
    navigate(`/news/${post.slug.current}`);
  };

  return (
    <li
      className="cursor-pointer rounded-xl border-2 p-4 py-2 transition-colors hover:border-blue-400"
      onClick={handleClick}
    >
      <div className="flex w-full justify-between">
        <h3 className="font-semibold">{post.title}</h3>
        <span className="text-muted-foreground w-30 text-end">
          {formatDistanceToNow(new Date(post.publishedAt), { addSuffix: true })}
        </span>
      </div>
    </li>
  );
}
