import { Label } from "@/components/ui/label";
import { useState, useEffect } from "react";
import TeamRankingComponent from "./TeamRankingComponent";
import InfiniteScroll from "react-infinite-scroll-component";
import PlayerRankingComponent from "./PlayerRankingComponent";
import {
  usePublicPlayers,
  usePublicTeams,
  usePublicSeasons,
} from "@/services/hooks";
import { Spinner } from "@/components/ui/shadcn-io/spinner";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Button } from "@/components/ui/button";
import { Menu } from "lucide-react";

function Rankings() {
  const [isExpanded, setIsExpanded] = useState(false);
  const [seasonFilter, setSeasonFilter] = useState<string | undefined>(
    import.meta.env.VITE_CURRENT_SEASON_ID || undefined,
  );
  const [competitionFilter, setCompetitionFilter] = useState<
    string | undefined
  >(import.meta.env.VITE_DEFAULT_COMPETITION_ID || undefined);

  const getInitialRankingType = () => {
    const hash = window.location.hash.replace("#", "");
    if (hash === "team" || hash === "player") {
      return hash;
    }
    return "team";
  };

  const [rankingType, setRankingType] = useState(
    getInitialRankingType() || "team",
  );
  window.location.hash = rankingType;

  const resetFilters = () => {
    setSeasonFilter(import.meta.env.VITE_DEFAULT_SEASON_ID || undefined);
    setCompetitionFilter(undefined);
  };

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

        <div
          className={`matches-filter mt-4 w-full rounded-xl border-2 p-4 md:mt-0 md:w-auto ${isExpanded ? "max-h-[1000px]" : "max-h-16"} transition-all duration-300`}
        >
          <div
            className="mb-2 flex cursor-pointer items-center justify-between"
            onClick={() => setIsExpanded(!isExpanded)}
          >
            <h2 className="font-semibold">Filter Rankings</h2>

            <Menu />
          </div>
          <div
            className={`bg-background transition-all duration-200 ${isExpanded ? "opacity-100" : "pointer-events-none opacity-0"}`}
          >
            <RankingsFilter
              expanded={isExpanded}
              seasonFilter={seasonFilter}
              setSeasonFilter={setSeasonFilter}
              competitionFilter={competitionFilter}
              setCompetitionFilter={setCompetitionFilter}
              resetFilters={resetFilters}
            />
          </div>
        </div>
        <div className="mt-2 flex w-full">
          <div className="flex-4 space-y-3">
            {rankingType === "player" ? (
              <PlayerRankingBody
                seasonFilter={seasonFilter}
                competitionFilter={competitionFilter}
              />
            ) : (
              <TeamRankingBody
                seasonFilter={seasonFilter}
                competitionFilter={competitionFilter}
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
  competitionFilter?: string;
}

function TeamRankingBody({
  seasonFilter,
  competitionFilter,
}: RankingBodyProps) {
  const [page, setPage] = useState(1);
  const [teams, setTeams] = useState<any[]>([]);
  const [hasMore, setHasMore] = useState(true);

  // Build query params with filters
  const queryParams = {
    sort: "elo" as const,
    order: "desc" as const,
    page,
    page_size: 20,
    ...(seasonFilter &&
      seasonFilter !== "all_seasons" && { season_id: seasonFilter }),
    ...(competitionFilter &&
      competitionFilter !== "all_competitions" && {
        competition_name: competitionFilter,
      }),
  };

  const { data, isLoading, error } = usePublicTeams(queryParams, {
    staleTime: 1000 * 60 * 5,
    keepPreviousData: true,
  });

  // Reset pagination when filters change
  useEffect(() => {
    setPage(1);
    setTeams([]);
    setHasMore(true);
  }, [seasonFilter, competitionFilter]);

  // Update teams when data changes
  useEffect(() => {
    if (data?.results) {
      setTeams((prevTeams) =>
        page === 1 ? data.results : [...prevTeams, ...data.results],
      );
      setHasMore(data.results.length > 0 && data.results.length === 20);
    }
  }, [data, page]);

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
        <TeamRankingComponent key={team.id || i} team={team} rank={i} />
      ))}
    </InfiniteScroll>
  );
}

function PlayerRankingBody({
  seasonFilter,
  competitionFilter,
}: RankingBodyProps) {
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
    ...(competitionFilter &&
      competitionFilter !== "all_competitions" && {
        competition_id: competitionFilter,
      }),
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
  }, [seasonFilter, competitionFilter]);

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
  expanded: boolean;
  seasonFilter?: string;
  setSeasonFilter: (value: string | undefined) => void;
  competitionFilter?: string;
  setCompetitionFilter: (value: string | undefined) => void;
  resetFilters: () => void;
}

function RankingsFilter(props: RankingsFilterProps) {
  // Get available seasons for the dropdown
  const { data: seasonsData } = usePublicSeasons({
    sort: "start_date",
    order: "desc",
    page_size: 50,
  });

  return (
    <div
      className={`mt-4 flex flex-wrap justify-center space-x-2 space-y-2 ${props.expanded ? "" : "pointer-events-none"}`}
    >
      <div className="space-y-1">
        <Label htmlFor="season">Season</Label>
        <Select
          value={props.seasonFilter}
          onValueChange={props.setSeasonFilter}
        >
          <SelectTrigger id="season">
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

      <div className="space-y-1">
        <Label className="invisible">Reset</Label>
        <Button
          variant="destructive"
          className="cursor-pointer"
          onClick={props.resetFilters}
        >
          Reset Filters
        </Button>
      </div>
    </div>
  );
}
