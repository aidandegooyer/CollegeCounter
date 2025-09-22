import { Label } from "@/components/ui/label";
import { useState, useEffect } from "react";
import TeamRankingComponent from "./TeamRankingComponent";
import InfiniteScroll from "react-infinite-scroll-component";
import PlayerRankingComponent from "./PlayerRankingComponent";
import {
  usePublicPlayers,
  usePublicTeams,
  usePublicSeasons,
  usePublicRankings,
  usePublicRankingItems,
} from "@/services/hooks";
import { Spinner } from "@/components/ui/shadcn-io/spinner";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

function Rankings() {
  const [seasonFilter, setSeasonFilter] = useState<string | undefined>(
    import.meta.env.VITE_CURRENT_SEASON_ID || undefined,
  );
  const [rankingWeekFilter, setRankingWeekFilter] = useState<
    string | undefined
  >(undefined);

  const getInitialRankingType = () => {
    const hash = window.location.hash.replace("#", "");
    if (hash === "team" || hash === "player") {
      return hash;
    }
    return "team";
  };

  document.title = "Rankings - College Counter";

  const [rankingType, setRankingType] = useState(
    getInitialRankingType() || "team",
  );
  window.location.hash = rankingType;

  return (
    <div className="app-container mx-4 flex justify-center">
      <div className="rankings w-full max-w-[1000px] justify-center">
        <div className="flex justify-center">
          <div className="my-4 flex h-12 w-[500px] rounded-xl border-2">
            <div
              onClick={() => setRankingType("team")}
              className={`group flex flex-1 items-center justify-center rounded-lg ${rankingType === "team" ? "bg-muted" : "cursor-pointer"}`}
            >
              <h2
                className={`transition-colors duration-200 ${
                  rankingType === "team"
                    ? ""
                    : "text-muted-foreground group-hover:text-foreground"
                }`}
              >
                Team Rankings
              </h2>
            </div>
            <div
              onClick={() => setRankingType("player")}
              className={`group flex flex-1 items-center justify-center rounded-lg ${rankingType === "player" ? "bg-muted" : "cursor-pointer"}`}
            >
              <h2
                className={`transition-colors duration-200 ${
                  rankingType === "player"
                    ? ""
                    : "text-muted-foreground group-hover:text-foreground"
                }`}
              >
                Player Rankings
              </h2>
            </div>
          </div>
        </div>

        <h1>{rankingType === "team" ? `Team Rankings` : "Player Rankings"}</h1>
        <h2 className="text-muted-foreground">
          {rankingType === "team"
            ? "Based on initial Faceit Elo and Team Performance"
            : "Based on current Faceit Elo"}
        </h2>

        {/* Clean Filter Box */}
        <div className="mt-4 w-full rounded-xl border-2 p-4">
          <RankingsFilter
            rankingType={rankingType}
            seasonFilter={seasonFilter}
            setSeasonFilter={setSeasonFilter}
            rankingWeekFilter={rankingWeekFilter}
            setRankingWeekFilter={setRankingWeekFilter}
          />
        </div>

        <div className="mt-2 flex w-full">
          <div className="flex-4 space-y-3">
            {rankingType === "player" ? (
              <PlayerRankingBody seasonFilter={seasonFilter} />
            ) : (
              <TeamRankingBody
                seasonFilter={seasonFilter}
                rankingWeekFilter={rankingWeekFilter}
              />
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

export default Rankings;

interface RankingBodyProps {
  seasonFilter?: string;
  rankingWeekFilter?: string;
}

function TeamRankingBody({
  seasonFilter,
  rankingWeekFilter,
}: RankingBodyProps) {
  const [page, setPage] = useState(1);
  const [teams, setTeams] = useState<any[]>([]);
  const [hasMore, setHasMore] = useState(true);

  // Determine if we're showing current rankings or a specific ranking snapshot
  const isCurrentRankings =
    !rankingWeekFilter || rankingWeekFilter === "current";

  // Query for current team rankings (live ELO data)
  const currentRankingsParams = {
    sort: "elo" as const,
    order: "desc" as const,
    page,
    page_size: 20,
    ...(seasonFilter &&
      seasonFilter !== "all_seasons" && { season_id: seasonFilter }),
  };

  // Query for historical ranking data
  const historicalRankingsParams = {
    ranking_id: rankingWeekFilter || "",
    page,
    page_size: 20,
    sort: "rank" as const,
    order: "asc" as const,
  };

  // Fetch current team data
  const {
    data: currentData,
    isLoading: isLoadingCurrent,
    error: currentError,
  } = usePublicTeams(currentRankingsParams, {
    staleTime: 1000 * 60 * 5,
    keepPreviousData: true,
    enabled: isCurrentRankings,
  });

  // Fetch historical ranking items
  const {
    data: historicalData,
    isLoading: isLoadingHistorical,
    error: historicalError,
  } = usePublicRankingItems(historicalRankingsParams, {
    staleTime: 1000 * 60 * 5,
    keepPreviousData: true,
    enabled: !isCurrentRankings && !!rankingWeekFilter,
  });

  // Use the appropriate data source
  const data = isCurrentRankings ? currentData : historicalData;
  const isLoading = isCurrentRankings ? isLoadingCurrent : isLoadingHistorical;
  const error = isCurrentRankings ? currentError : historicalError;

  // Reset pagination when filters change
  useEffect(() => {
    setPage(1);
    setTeams([]);
    setHasMore(true);
  }, [seasonFilter, rankingWeekFilter]);

  // Update teams when data changes
  useEffect(() => {
    if (data?.results) {
      let processedResults;

      if (isCurrentRankings) {
        // For current rankings, use team data directly
        processedResults = data.results;
      } else {
        // For historical rankings, extract team data from ranking items
        processedResults = data.results.map((item: any) => ({
          id: item.team.id,
          name: item.team.name,
          picture: item.team.picture,
          school_name: item.team.school_name,
          elo: item.elo, // Use historical ELO from ranking
          rank: item.rank, // Historical rank
        }));
      }

      setTeams((prevTeams) =>
        page === 1 ? processedResults : [...prevTeams, ...processedResults],
      );
      setHasMore(processedResults.length > 0 && processedResults.length === 20);
    }
  }, [data, page, isCurrentRankings]);

  const loadMoreTeams = () => {
    if (!isLoading && hasMore) {
      setPage((prevPage) => prevPage + 1);
    }
  };

  if (error) return <div>Error loading teams</div>;

  return (
    <InfiniteScroll
      dataLength={teams.length}
      hasMore={hasMore}
      next={loadMoreTeams}
      loader={
        <div className="flex h-10 justify-center">
          <Spinner />
        </div>
      }
      endMessage={
        <div className="text-muted-foreground my-4 text-center">
          No more teams to load
        </div>
      }
      className="infinite-scroll-container space-y-2"
    >
      {teams.map((team, i) => (
        <TeamRankingComponent
          key={team.id || i}
          team={team}
          rank={isCurrentRankings ? i + 1 : team.rank || i}
        />
      ))}
    </InfiniteScroll>
  );
}

function PlayerRankingBody({ seasonFilter }: RankingBodyProps) {
  const [page, setPage] = useState(1);
  const [players, setPlayers] = useState<any[]>([]);
  const [hasMore, setHasMore] = useState(true);

  // Build query params with filters
  const queryParams = {
    sort: "elo" as const,
    order: "desc" as const,
    page,
    page_size: 20,
    ...(seasonFilter &&
      seasonFilter !== "all_seasons" && { season_id: seasonFilter }),
  };

  const { data, isLoading, error } = usePublicPlayers(queryParams, {
    staleTime: 1000 * 60 * 5,
    keepPreviousData: true,
  });

  // Reset pagination when filters change
  useEffect(() => {
    setPage(1);
    setPlayers([]);
    setHasMore(true);
  }, [seasonFilter]);

  // Update teams when data changes
  useEffect(() => {
    if (data?.results) {
      setPlayers((prevPlayers) =>
        page === 1 ? data.results : [...prevPlayers, ...data.results],
      );
      setHasMore(data.results.length > 0 && data.results.length === 20);
    }
  }, [data, page]);

  const loadMorePlayers = () => {
    if (!isLoading && hasMore) {
      setPage((prevPage) => prevPage + 1);
    }
  };

  if (error) return <div>Error loading teams</div>;

  return (
    <InfiniteScroll
      dataLength={players.length}
      hasMore={hasMore}
      next={loadMorePlayers}
      loader={
        <div className="flex h-10 justify-center">
          <Spinner />
        </div>
      }
      endMessage={
        <div className="text-muted-foreground my-4 text-center">
          No more players to load
        </div>
      }
      className="infinite-scroll-container space-y-2"
    >
      {players.map((player, i) => (
        <PlayerRankingComponent key={player.id || i} {...player} rank={i} />
      ))}
    </InfiniteScroll>
  );
}

interface RankingsFilterProps {
  rankingType: string;
  seasonFilter?: string;
  setSeasonFilter: (value: string | undefined) => void;
  rankingWeekFilter?: string;
  setRankingWeekFilter: (value: string | undefined) => void;
}

function RankingsFilter(props: RankingsFilterProps) {
  // Get available seasons for the dropdown
  const { data: seasonsData } = usePublicSeasons({
    sort: "start_date",
    order: "desc",
    page_size: 50,
  });

  // Fetch rankings for the selected season
  const { data: rankingsData } = usePublicRankings(
    {
      season_id: props.seasonFilter,
      sort: "date",
      order: "desc",
      page_size: 100,
    },
    {
      enabled: !!props.seasonFilter, // Only fetch if season is selected
    },
  );

  return (
    <div className="flex flex-wrap justify-center gap-4">
      {/* Season Filter - Always shown */}
      <div className="space-y-1">
        <Label htmlFor="season">Season</Label>
        <Select
          value={props.seasonFilter}
          onValueChange={props.setSeasonFilter}
        >
          <SelectTrigger id="season" className="w-48">
            <SelectValue placeholder="Select a season" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem disabled value="x">
              Select a season
            </SelectItem>
            {seasonsData?.results?.map((season) => (
              <SelectItem key={season.id} value={season.id}>
                {season.name}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      {/* Ranking Week Filter - Only for team rankings */}
      {props.rankingType === "team" && (
        <div className="space-y-1">
          <Label htmlFor="rankingWeek">Ranking Week</Label>
          <Select
            value={props.rankingWeekFilter}
            onValueChange={props.setRankingWeekFilter}
          >
            <SelectTrigger id="rankingWeek" className="w-48">
              <SelectValue placeholder="Select a week" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem disabled value="x">
                Select a week
              </SelectItem>
              <SelectItem value="current">Current Rankings</SelectItem>
              {rankingsData?.results?.map((ranking) => (
                <SelectItem key={ranking.id} value={ranking.id}>
                  {new Date(ranking.date).toLocaleDateString("en-US", {
                    month: "short",
                    day: "numeric",
                    year: "numeric",
                  })}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      )}
    </div>
  );
}
