import { ChevronRight } from "lucide-react";
import logo from "@/assets/0.5x/C Logo@0.5x.png";

function NewsWidget() {
  return (
    <div className="news-widget">
      <div className="group flex cursor-pointer items-center justify-between">
        <h2>News</h2>
        <ChevronRight className="text-muted-foreground mr-2 h-6 w-6 transition-all group-hover:mr-0" />
      </div>
      <hr />
      <ul className="mt-2 space-y-2">
        <FeaturedNews />
        <NewsItem />
        <NewsItem />
      </ul>
    </div>
  );
}

export default NewsWidget;

function FeaturedNews() {
  return (
    <div className="featured-news rounded-xl border-2">
      <img
        src={logo}
        className="h-64 w-full rounded-xl object-cover"
        alt="Featured News"
      />
      <div className="p-4 pt-2">
        <h2 className="text-lg font-semibold">Featured News</h2>
        <p className="text-muted-foreground mt-2">
          This is a brief description of the featured news item.
        </p>
      </div>
    </div>
  );
}

function NewsItem() {
  return (
    <li className="flex cursor-pointer rounded-xl border-2 p-4 py-2">
      <div className="flex-1 space-y-2">
        <h3 className="font-semibold">News Title</h3>
        <p className="text-muted-foreground">
          Brief description of the news item.
        </p>
      </div>
      <div className="flex-1 text-end">
        <span className="text-muted-foreground">2025-10-01</span>
      </div>
    </li>
  );
}
