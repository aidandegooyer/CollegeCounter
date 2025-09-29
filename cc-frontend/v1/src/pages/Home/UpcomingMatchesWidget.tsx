import Logo from "@/components/Logo";
import { Alert, AlertTitle, AlertDescription } from "@/components/ui/alert";
import { Spinner } from "@/components/ui/shadcn-io/spinner";
import type { PublicMatch } from "@/services/api";
import { calculateMatchStars } from "@/services/elo";
import { usePublicMatches } from "@/services/hooks";
import { ChevronRight, Star } from "lucide-react";
import { useMemo } from "react";
import { NavLink, useNavigate } from "react-router";

interface UpcomingMatchesWidgetProps {
  teamId?: string;
  limit?: number;
}

function UpcomingMatchesWidget({ teamId, limit }: UpcomingMatchesWidgetProps) {
  const currentDate = useMemo(() => {
    const now = new Date();
    return now.toISOString();
  }, []);

  const { data, isLoading, error } = usePublicMatches(
    {
      sort: "date",
      order: "asc",
      page: 1,
      page_size: limit || 4,
      status: "scheduled",
      date_from: currentDate,
      team_id: teamId,
    },
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
          <Match
            key={index}
            match={match}
            stars={calculateMatchStars(
              match.team1?.elo || 1000,
              match.team2?.elo || 1000,
            )}
          />
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

interface MatchProps {
  match: PublicMatch;
  stars: number;
}

function Match(props: MatchProps) {
  const scheduledDate = new Date(props.match.date);
  const dateString = scheduledDate.toLocaleDateString(undefined, {
    month: "short",
    day: "numeric",
  });
  const timeString = scheduledDate.toLocaleTimeString(undefined, {
    hour: "2-digit",
    minute: "2-digit",
  });

  const navigate = useNavigate();

  const handleClick = () => {
    navigate(`/matches/${props.match.id}`);
  };

  return (
    <li
      className="flex cursor-pointer rounded-xl border-2 p-4 py-2"
      onClick={handleClick}
    >
      <div className="flex-3 space-y-3">
        <div className="flex items-center space-x-2">
          <Logo
            src={props.match.team1.picture}
            className="h-6 w-6 rounded-sm"
            alt="Logo"
            type="team"
          />
          <span className="max-w-[120px] truncate overflow-ellipsis whitespace-nowrap">
            {props.match.team1.name}
          </span>
        </div>
        <div className="flex items-center space-x-2 overflow-ellipsis">
          <Logo
            src={props.match.team2.picture}
            className="h-6 w-6 rounded-sm"
            alt="Logo"
            type="team"
          />
          <span className="max-w-[120px] truncate overflow-ellipsis whitespace-nowrap">
            {props.match.team2.name}
          </span>
        </div>
      </div>
      <div className="flex-1 text-end text-sm">
        <span className="text-muted-foreground">{dateString}</span>
        <br />
        <span className="text-muted-foreground">{timeString}</span>
        <br />

        <span className="text-muted-foreground space-x-.5 mt-1 flex items-center justify-end">
          {Array.from({ length: props.stars }).map((_, i) => (
            <Star key={i} size={14} className="fill-muted-foreground" />
          ))}
          {Array.from({ length: 5 - props.stars }).map((_, i) => (
            <Star key={i} size={14} className="text-gray-700" />
          ))}
        </span>
      </div>
    </li>
  );
}

export default UpcomingMatchesWidget;
