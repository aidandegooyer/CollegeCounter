import Logo from "@/components/Logo";
import { Alert, AlertTitle, AlertDescription } from "@/components/ui/alert";
import { Spinner } from "@/components/ui/shadcn-io/spinner";
import type { PublicMatch } from "@/services/api";
import { usePublicMatches } from "@/services/hooks";
import { ChevronRight } from "lucide-react";
import { NavLink, useNavigate } from "react-router";

interface ResultsWidgetProps {
  teamId?: string;
  limit?: number;
}

function ResultsWidget({ teamId, limit }: ResultsWidgetProps) {
  const { data, isLoading, error } = usePublicMatches(
    {
      sort: "date",
      order: "desc",
      page: 1,
      page_size: limit || 4,
      status: "completed",
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
        to="/matches#past"
        className="group flex cursor-pointer items-center justify-between"
      >
        <h2>Past Matches</h2>
        <ChevronRight className="text-muted-foreground mr-2 h-6 w-6 transition-all group-hover:mr-0" />
      </NavLink>
      <hr />
      <ul className="mt-2 space-y-2">{renderMatches()}</ul>
    </div>
  );
}

function Match(match: PublicMatch) {
  const winningTeamId = match.winner?.id;
  let winner, loser;
  if (winningTeamId === match.team1.id) {
    winner = match.team1;
    loser = match.team2;
  } else {
    winner = match.team2;
    loser = match.team1;
  }

  const navigate = useNavigate();

  const handleClick = () => {
    navigate(`/matches/${match.id}`);
  };
  return (
    <li
      className="flex cursor-pointer rounded-xl border-2 p-4 py-2"
      onClick={handleClick}
    >
      <div className="flex-3 space-y-2">
        <div className="flex items-center space-x-2">
          <Logo
            src={winner.picture}
            className="h-6 w-6 rounded-sm"
            alt="Logo"
            type="team"
          />
          <span className="truncate overflow-ellipsis whitespace-nowrap font-semibold">
            {winner.name}
          </span>
        </div>
        <div className="flex items-center space-x-2 overflow-ellipsis">
          <Logo
            src={loser.picture}
            className="h-6 w-6 rounded-sm"
            alt="Logo"
            type="team"
          />
          <span className="text-muted-foreground truncate overflow-ellipsis whitespace-nowrap">
            {loser.name}
          </span>
        </div>
      </div>
      <div className="flex-1 space-y-2 text-end">
        <span className="flex justify-end">
          <p className="bg-muted ml-2 rounded-sm px-1 font-mono text-green-500">
            {Math.max(match.score_team2, match.score_team1)}
          </p>
        </span>
        <span className="flex justify-end">
          <p className="bg-muted ml-2 rounded-sm px-1 font-mono text-red-500">
            {Math.min(match.score_team2, match.score_team1)}
          </p>
        </span>
      </div>
    </li>
  );
}

export default ResultsWidget;
