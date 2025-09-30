import Logo from "@/components/Logo";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Spinner } from "@/components/ui/shadcn-io/spinner";
import type { PublicRankingItem } from "@/services/api";
import { usePublicRankingItems, usePublicRankings } from "@/services/hooks";
import { ChevronRight } from "lucide-react";
import { NavLink } from "react-router";

function TeamRankingsWidget() {
  const {
    data: rankingsData,
    isLoading: rankingsIsLoading,
    error: rankingsError,
  } = usePublicRankings({
    season_id: import.meta.env.VITE_CURRENT_SEASON_ID,
    sort: "date",
    order: "desc",
    page_size: 1,
  });

  const {
    data: rankingItems,
    isLoading: rankingItemsIsLoading,
    error: rankingItemsError,
  } = usePublicRankingItems(
    {
      ranking_id: rankingsData?.results[0]?.id || "",
      sort: "rank",
      order: "asc",
      page_size: 10,
    },
    {
      enabled: !!rankingsData?.results[0]?.id,
    },
  );

  if (!rankingsData || rankingsData.results.length === 0) {
    return (
      <div className="rankings-widget h-103 rounded-xl border-2 px-4 py-2">
        <NavLink
          to="/rankings#team"
          className="group flex cursor-pointer items-center justify-between"
        >
          <h2>Team Rankings</h2>
          <ChevronRight className="text-muted-foreground mr-2 h-6 w-6 transition-all group-hover:mr-0" />
        </NavLink>
        <hr />
        <div>
          <Spinner className="mx-auto my-4" />
        </div>
      </div>
    );
  }

  if (rankingsError || rankingItemsError) {
    return (
      <div className="rankings-widget h-103 rounded-xl border-2 px-4 py-2">
        <NavLink
          to="/rankings#team"
          className="group flex cursor-pointer items-center justify-between"
        >
          <h2>Team Rankings</h2>
          <ChevronRight className="text-muted-foreground mr-2 h-6 w-6 transition-all group-hover:mr-0" />
        </NavLink>
        <hr />
        <Alert variant="destructive" className="mt-4">
          <AlertTitle className="text-lg">Error</AlertTitle>
          <AlertDescription>
            There was an error loading the team rankings. Please try again
            later.
          </AlertDescription>
        </Alert>
      </div>
    );
  }
  if (
    rankingsIsLoading ||
    !rankingsData ||
    rankingItemsIsLoading ||
    !rankingItems
  ) {
    return (
      <div className="rankings-widget h-103 rounded-xl border-2 px-4 py-2">
        <NavLink
          to="/rankings#team"
          className="group flex cursor-pointer items-center justify-between"
        >
          <h2>Team Rankings</h2>
          <ChevronRight className="text-muted-foreground mr-2 h-6 w-6 transition-all group-hover:mr-0" />
        </NavLink>
        <hr />
        <div>
          <Spinner className="mx-auto my-4" />
        </div>
      </div>
    );
  }

  return (
    <div className="rankings-widget h-103 rounded-xl border-2 px-4 py-2">
      <NavLink
        to="/rankings#team"
        className="group flex cursor-pointer items-center justify-between"
      >
        <h2>Team Rankings</h2>
        <ChevronRight className="text-muted-foreground mr-2 h-6 w-6 transition-all group-hover:mr-0" />
      </NavLink>
      <hr />
      <ul className="space-y-3 py-2 pt-3">
        {rankingItems.results.map((team, i) => (
          <RankingItem key={team.id || i} index={i} team={team} />
        ))}
      </ul>
    </div>
  );
}

interface RankingItemProps {
  index: number;
  team: PublicRankingItem;
}

function RankingItem(props: RankingItemProps) {
  const rank = props.index + 1;

  return (
    <li className="flex justify-between">
      <NavLink to={`/teams/${props.team.id}`} className="group cursor-pointer">
        <div className="flex items-center space-x-2">
          <span className="mr-3 w-4 text-end font-mono">{rank}</span>
          <Logo
            src={props.team.team?.picture || undefined}
            className="h-6 w-6 rounded-sm"
            alt="pfp"
            type="team"
          />
          <div className="max-w-[128px] truncate overflow-ellipsis whitespace-nowrap transition-colors group-hover:text-blue-400">
            {props.team.team.name}
          </div>
        </div>
      </NavLink>

      <div>
        <span className="bg-secondary drop-shadow-secondary drop-shadow-lg/50 rounded-md p-1 font-mono text-sm">
          {props.team.elo}
        </span>
      </div>
    </li>
  );
}

export default TeamRankingsWidget;
