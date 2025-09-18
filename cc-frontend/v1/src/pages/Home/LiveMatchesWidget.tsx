import Logo from "@/components/Logo";
import { Alert, AlertTitle, AlertDescription } from "@/components/ui/alert";
import { Spinner } from "@/components/ui/shadcn-io/spinner";
import type { PublicMatch } from "@/services/api";
import { usePublicMatches } from "@/services/hooks";
import { Radio } from "lucide-react";
import "./LiveMatchesWidget.css";
import { NavLink } from "react-router";

function LiveMatchesWidget() {
  const { data, isLoading, error } = usePublicMatches(
    {
      sort: "date",
      order: "asc",
      page: 1,
      page_size: 4,
      status: "in_progress",
    },
    {
      staleTime: 1000 * 30, // Refresh every 30 seconds for live data
    },
  );

  // Don't render the widget if there are no live matches
  if (!isLoading && (!data?.results || data.results.length === 0)) {
    return null;
  }

  function renderMatches() {
    if (isLoading) {
      return (
        <div className="flex h-20 items-center justify-center">
          <Spinner />
        </div>
      );
    }

    if (error) {
      return (
        <div className="mt-2">
          <Alert variant="destructive">
            <AlertTitle className="text-sm">Error</AlertTitle>
            <AlertDescription className="text-xs">
              Unable to load live matches.
            </AlertDescription>
          </Alert>
        </div>
      );
    }

    if (!data?.results || data.results.length === 0) {
      return null;
    }

    return (
      <>
        {data.results.map((match) => (
          <Match key={match.id} {...match} />
        ))}
      </>
    );
  }

  return (
    <div className="matches-widget">
      <NavLink
        to="matches#live"
        className="flex cursor-pointer items-center justify-between"
      >
        <h2>Live Matches</h2>
        <Radio className="animate-radio-blink mr-2 h-6 w-6 text-red-500" />
      </NavLink>
      <hr />
      <ul className="mt-2 space-y-2">{renderMatches()}</ul>
    </div>
  );
}

function Match(match: PublicMatch) {
  return (
    <li className="flex rounded-xl border-2 p-4 py-2">
      <div className="flex-3 space-y-2">
        <div className="flex items-center space-x-2">
          <Logo
            src={match.team1.picture}
            className="h-6 w-6 rounded-sm"
            alt="Logo"
            type="team"
          />
          <span className="max-w-[120px] truncate overflow-ellipsis whitespace-nowrap">
            {match.team1.name}
          </span>
        </div>
        <div className="flex items-center space-x-2 overflow-ellipsis">
          <Logo
            src={match.team2.picture}
            className="h-6 w-6 rounded-sm"
            alt="Logo"
            type="team"
          />
          <span className="max-w-[120px] truncate overflow-ellipsis whitespace-nowrap">
            {match.team2.name}
          </span>
        </div>
      </div>
      <div className="flex-1 space-y-2 text-end">
        <span className="flex justify-end">
          <p
            className={`font-mono ${
              match.score_team1 === match.score_team2
                ? "text-muted-foreground"
                : match.score_team1 &&
                    match.score_team1 > (match.score_team2 || 0)
                  ? "text-green-500"
                  : "text-red-500"
            }`}
          >
            {match.score_team1 || 0}
          </p>
        </span>
        <span className="flex justify-end">
          <p
            className={`font-mono ${
              match.score_team1 === match.score_team2
                ? "text-muted-foreground"
                : match.score_team2 &&
                    match.score_team2 > (match.score_team1 || 0)
                  ? "text-green-500"
                  : "text-red-500"
            }`}
          >
            {match.score_team2 || 0}
          </p>
        </span>
      </div>
    </li>
  );
}

export default LiveMatchesWidget;
