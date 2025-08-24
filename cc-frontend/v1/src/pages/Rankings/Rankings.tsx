import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group";
import { Label } from "@/components/ui/label";

import { useState, useEffect } from "react";
import TeamRankingComponent from "./TeamRankingComponent";
import InfiniteScroll from "react-infinite-scroll-component";
import PlayerRankingComponent from "./PlayerRankingComponent";
import { usePublicPlayers, usePublicTeams } from "@/services/hooks";
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

  return (
    <div className="app-container mx-16 flex justify-center">
      <div className="rankings w-full max-w-[900px] justify-center">
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
          className={`matches-filter mt-4 w-full cursor-pointer rounded-xl border-2 p-4 md:mt-0 md:w-auto ${isExpanded ? "max-h-[1000px]" : "max-h-16"} transition-all duration-300`}
          onClick={() => setIsExpanded(!isExpanded)}
        >
          <div className="mb-2 flex items-center justify-between">
            <h2 className="font-semibold">Filter Matches</h2>

            <Menu />
          </div>
          <div
            className={`bg-background transition-all duration-200 ${isExpanded ? "opacity-100" : "pointer-events-none opacity-0"}`}
          >
            <RankingsFilter expanded={isExpanded} />
          </div>
        </div>
        <div className="mt-2 flex w-full">
          <div className="flex-4 space-y-3">
            {rankingType === "player" ? (
              <PlayerRankingBody />
            ) : (
              <TeamRankingBody />
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

export default Rankings;

function TeamRankingBody() {
  const [page, setPage] = useState(1);
  const [teams, setTeams] = useState<any[]>([]);
  const [hasMore, setHasMore] = useState(true);

  const { data, isLoading, error } = usePublicTeams(
    { sort: "elo", order: "desc", page, page_size: 20 },
    {
      staleTime: 1000 * 60 * 5,
      keepPreviousData: true,
    },
  );

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

function PlayerRankingBody() {
  const [page, setPage] = useState(1);
  const [players, setPlayers] = useState<any[]>([]);
  const [hasMore, setHasMore] = useState(true);

  const { data, isLoading, error } = usePublicPlayers(
    { sort: "elo", order: "desc", page, page_size: 20 },
    {
      staleTime: 1000 * 60 * 5,
      keepPreviousData: true,
    },
  );

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
}

function RankingsFilter(props: RankingsFilterProps) {
  return (
    <div
      className={`mt-4 flex flex-wrap justify-center space-x-2 space-y-2 ${props.expanded ? "" : "pointer-events-none"}`}
    >
      <div className="space-y-1">
        <Label htmlFor="season">Season</Label>
        <Select>
          <SelectTrigger id="season">
            <SelectValue placeholder="Select a season" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all_seasons">All Seasons</SelectItem>
            <SelectItem value="necc">Spring 2025</SelectItem>
            <SelectItem value="playfly">Fall 2025</SelectItem>
          </SelectContent>
        </Select>
      </div>

      <div className="space-y-1">
        <Label htmlFor="competition">Competition</Label>
        <Select>
          <SelectTrigger id="competition">
            <SelectValue placeholder="Select a competition" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all_competitions">All Competitions</SelectItem>
            <SelectItem value="necc">NECC</SelectItem>
            <SelectItem value="playfly">Playfly</SelectItem>
          </SelectContent>
        </Select>
      </div>

      <div className="space-y-1">
        <Label className="invisible">Reset</Label>
        <Button variant="destructive" className="cursor-pointer">
          Reset Filters
        </Button>
      </div>
    </div>
  );
}
