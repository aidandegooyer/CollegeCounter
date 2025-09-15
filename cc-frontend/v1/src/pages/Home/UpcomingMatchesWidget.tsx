import Logo from "@/components/Logo";
import { Alert, AlertTitle, AlertDescription } from "@/components/ui/alert";
import { Spinner } from "@/components/ui/shadcn-io/spinner";
import type { PublicMatch } from "@/services/api";
import { usePublicMatches } from "@/services/hooks";
import { ChevronRight, Star } from "lucide-react";
import { NavLink } from "react-router";

function UpcomingMatchesWidget() {
  const { data, isLoading, error } = usePublicMatches(
    { sort: "date", order: "asc", page: 1, page_size: 4, status: "scheduled" },
    {
      staleTime: 1000 * 60 * 5,
    },
  );

  function renderMatches() {
    if (isLoading || !data) {
      return (
        <div className="flex h-40 items-center justify-center">
          <Spinner />
        </div>
      );
    }
    if (error) {
      return (
        <div className="mt-4">
          <Alert variant="destructive" className="mt-4">
            <AlertTitle className="text-lg">Error</AlertTitle>
            <AlertDescription>
              There was an error loading the player rankings. Please try again
              later.
            </AlertDescription>
          </Alert>
        </div>
      );
    }
    if (data.results.length === 0) {
      return (
        <div className="text-muted-foreground mt-4 text-center">
          No upcoming matches
        </div>
      );
    }

    return (
      <>
        {data.results.map((match, index) => (
          <Match key={index} {...match} />
        ))}
      </>
    );
  }

  return (
    <div className="matches-widget">
      <NavLink
        to="/matches"
        className="group flex cursor-pointer items-center justify-between"
      >
        <h2>Upcoming Matches</h2>
        <ChevronRight className="text-muted-foreground mr-2 h-6 w-6 transition-all group-hover:mr-0" />
      </NavLink>
      <hr />
      <ul className="mt-2 space-y-2">
        <ul className="mt-2 space-y-2">{renderMatches()}</ul>
      </ul>
    </div>
  );
}

function Match(match: PublicMatch) {
  const scheduledDate = new Date(match.date);
  const dateString = scheduledDate.toLocaleDateString(undefined, {
    month: "short",
    day: "numeric",
  });
  const timeString = scheduledDate.toLocaleTimeString(undefined, {
    hour: "2-digit",
    minute: "2-digit",
  });
  return (
    <li className="flex rounded-xl border-2 p-4 py-2">
      <div className="flex-3 space-y-3">
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
      <div className="flex-1 text-end text-sm">
        <span className="text-muted-foreground">{dateString}</span>
        <br />
        <span className="text-muted-foreground">{timeString}</span>
        <br />

        <span className="text-muted-foreground space-x-.5 mt-1 flex items-center justify-end">
          <Star size={14} />
          <Star size={14} />
          <Star size={14} />
          <Star size={14} />
          <Star size={14} />
        </span>
      </div>
    </li>
  );
}

export default UpcomingMatchesWidget;
