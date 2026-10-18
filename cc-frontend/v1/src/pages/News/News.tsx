import logo from "@/assets/0.5x/C Logo@0.5x.png";
import { Spinner } from "@/components/ui/shadcn-io/spinner";
import client from "@/services/sanity-client";
import { format, formatDistanceToNowStrict } from "date-fns";
import { useState, useEffect, type ReactNode } from "react";
import { Link } from "react-router";
import AuthorName from "./AuthorName";
import { useDocumentTitle } from "@/hooks/useDocumentTitle";
import { sanityImageProps } from "@/lib/images";

interface SanityPost {
  _id: string;
  title: string;
  slug: { _type: "slug"; current: string };
  excerpt?: string;
  imageUrl?: string;
  author?: string;
  authorLink?: string;
  publishedAt: string;
}

// How many posts fill each section of the front page; the rest go in the archive
const SIDEBAR_COUNT = 4;
const GRID_COUNT = 6;

function News() {
  const [posts, setPosts] = useState<SanityPost[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useDocumentTitle("News");

  useEffect(() => {
    const fetchPosts = async (start: number, amount: number) => {
      try {
        setLoading(true);
        const query = `*[_type == "post"] | order(publishedAt desc)[${start}...${start + amount}]{
          _id,
          title,
          slug,
          "excerpt": array::join(string::split(pt::text(body), "")[0...300], ""),
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

    fetchPosts(0, 50);
  }, []);

  const renderContent = () => {
    if (loading) {
      return (
        <div className="flex h-64 items-center justify-center">
          <Spinner className="h-8 w-8" />
        </div>
      );
    }

    if (error) {
      return <div className="mt-8 text-center text-red-500">{error}</div>;
    }

    if (posts.length === 0) {
      return (
        <div className="text-muted-foreground mt-8 text-center">
          No news posts available
        </div>
      );
    }

    const [lead, ...rest] = posts;
    const sidebar = rest.slice(0, SIDEBAR_COUNT);
    const grid = rest.slice(SIDEBAR_COUNT, SIDEBAR_COUNT + GRID_COUNT);
    const archive = rest.slice(SIDEBAR_COUNT + GRID_COUNT);

    return (
      <>
        <section className="grid gap-6 py-6 lg:grid-cols-3">
          {/* Without a sidebar the lead takes the whole row */}
          <div
            className={`flex flex-col ${sidebar.length > 0 ? "lg:col-span-2" : "lg:col-span-3"}`}
          >
            <SectionLabel>Featured</SectionLabel>
            <LeadStory post={lead} />
          </div>
          {sidebar.length > 0 && (
            <aside>
              <SectionLabel>Latest</SectionLabel>
              <ul className="space-y-4">
                {sidebar.map((post) => (
                  <li key={post._id}>
                    <SidebarStory post={post} />
                  </li>
                ))}
              </ul>
            </aside>
          )}
        </section>

        {grid.length > 0 && (
          <section className="py-6">
            <SectionLabel>More Stories</SectionLabel>
            <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
              {grid.map((post) => (
                <GridStory key={post._id} post={post} />
              ))}
            </div>
          </section>
        )}

        {archive.length > 0 && (
          <section className="py-6">
            <SectionLabel>From the Archive</SectionLabel>
            <ul className="gap-x-6 sm:columns-2 lg:columns-3">
              {archive.map((post) => (
                <li key={post._id} className="mb-3 break-inside-avoid">
                  <Link
                    to={`/news/${post.slug.current}`}
                    className="block rounded-xl border-2 p-4 py-2 transition-colors hover:border-blue-400"
                  >
                    <h3 className="font-semibold">{post.title}</h3>
                    <div className="text-muted-foreground mt-1 text-sm">
                      {format(new Date(post.publishedAt), "MMM d, yyyy")}
                    </div>
                  </Link>
                </li>
              ))}
            </ul>
          </section>
        )}
      </>
    );
  };

  return (
    <div className="flex justify-center">
      <div className="mx-4 w-full max-w-[1200px]">
        <h1 className="sr-only">News</h1>
        {renderContent()}
      </div>
    </div>
  );
}

export default News;

function SectionLabel({ children }: { children: ReactNode }) {
  return (
    <>
      <h2>{children}</h2>
      <hr className="mb-4" />
    </>
  );
}

// Post images are 1000x450; shown whole, never cropped. `sizes` is the
// displayed width, so the browser fetches no bigger a copy than it needs
function StoryImage({ post, sizes }: { post: SanityPost; sizes: string }) {
  return (
    <img
      {...sanityImageProps(post.imageUrl || logo, sizes)}
      className="aspect-[1000/450] w-full rounded-xl object-contain"
      alt={post.title}
    />
  );
}

function Byline({ post }: { post: SanityPost }) {
  return (
    <div className="mt-auto flex justify-between gap-4 pt-2">
      {/* Above the card's stretched link so it gets its own clicks */}
      <AuthorName
        author={post.author}
        authorLink={post.authorLink}
        className="text-foreground relative z-10 text-sm"
      />
      <span className="text-muted-foreground shrink-0 text-sm">
        {formatDistanceToNowStrict(new Date(post.publishedAt), {
          addSuffix: true,
        })}
      </span>
    </div>
  );
}

// The whole card is clickable through its title link's ::after, which covers
// the card; a link can't be nested in another for the author's link
const CARD =
  "relative flex flex-col rounded-xl border-2 transition-colors hover:border-blue-400";

function TitleLink({
  post,
  children,
}: {
  post: SanityPost;
  children: ReactNode;
}) {
  return (
    <Link
      to={`/news/${post.slug.current}`}
      className="after:absolute after:inset-0 after:rounded-xl after:content-['']"
    >
      {children}
    </Link>
  );
}

function LeadStory({ post }: { post: SanityPost }) {
  return (
    <article className={`${CARD} flex-1`}>
      <StoryImage post={post} sizes="(min-width: 1024px) 800px, 100vw" />
      <div className="flex flex-1 flex-col p-4 pt-2">
        <h3 className="text-2xl font-semibold">
          <TitleLink post={post}>{post.title}</TitleLink>
        </h3>
        {post.excerpt && (
          <p className="text-muted-foreground mt-2 line-clamp-3">
            {post.excerpt}
          </p>
        )}
        <Byline post={post} />
      </div>
    </article>
  );
}

function SidebarStory({ post }: { post: SanityPost }) {
  return (
    <article className={`${CARD} p-4 py-2`}>
      <h3 className="font-semibold">
        <TitleLink post={post}>{post.title}</TitleLink>
      </h3>
      {post.excerpt && (
        <p className="text-muted-foreground mt-1 line-clamp-2 text-sm">
          {post.excerpt}
        </p>
      )}
      <Byline post={post} />
    </article>
  );
}

function GridStory({ post }: { post: SanityPost }) {
  return (
    <article className={CARD}>
      <StoryImage
        post={post}
        sizes="(min-width: 1024px) 400px, (min-width: 640px) 50vw, 100vw"
      />
      <div className="flex flex-1 flex-col p-4 pt-2">
        <h3 className="font-semibold">
          <TitleLink post={post}>{post.title}</TitleLink>
        </h3>
        {post.excerpt && (
          <p className="text-muted-foreground mt-1 line-clamp-2 text-sm">
            {post.excerpt}
          </p>
        )}
        <Byline post={post} />
      </div>
    </article>
  );
}
