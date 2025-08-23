import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group";
import { Label } from "@/components/ui/label";

import { useState, useEffect } from "react";
import TeamRankingComponent from "./TeamRankingComponent";
import InfiniteScroll from "react-infinite-scroll-component";
import PlayerRankingComponent from "./PlayerRankingComponent";
import { usePublicPlayers, usePublicTeams } from "@/services/hooks";
import { Spinner } from "@/components/ui/shadcn-io/spinner";

function Rankings() {
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
      <div className="rankings w-full max-w-[1200px] justify-center">
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
        <div className="mt-2 flex w-full">
          <div className="flex-4 space-y-3">
            {rankingType === "player" ? (
              <PlayerRankingBody />
            ) : (
              <TeamRankingBody />
            )}
          </div>
          <div className="ml-8 hidden flex-1 space-y-4 lg:block">
            {rankingType === "team" ? (
              <TeamRankingsFilter />
            ) : (
              <PlayerRankingsFilter />
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
        <TeamRankingComponent key={team.id || i} {...team} />
      ))}
    </InfiniteScroll>
  );
}

function TeamRankingsFilter() {
  return (
    <div className="team-rankings-filter w-full rounded-xl border-2 p-4 py-2">
      <h2>Filter</h2>
      <hr />
      <h3 className="mt-2">Competition</h3>
      <RadioGroup className="my-2" defaultValue="all">
        <Label className="flex cursor-pointer space-x-2">
          <RadioGroupItem value="all" id="competition-all" />
          <span className="">All</span>
        </Label>
        <Label className="flex cursor-pointer space-x-2">
          <RadioGroupItem value="necc" id="competition-necc" />
          <span className="">NECC</span>
        </Label>
        <Label className="flex cursor-pointer space-x-2">
          <RadioGroupItem value="playfly" id="competition-playfly" />
          <span className="">Playfly</span>
        </Label>
      </RadioGroup>
    </div>
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

function PlayerRankingsFilter() {
  return (
    <div className="team-rankings-filter w-full rounded-xl border-2 p-4 py-2">
      <h2>Filter</h2>
      <hr />
      <h3 className="mt-2">Competition</h3>
      <RadioGroup className="my-2" defaultValue="all">
        <Label className="flex cursor-pointer space-x-2">
          <RadioGroupItem value="all" id="competition-all" />
          <span className="">All</span>
        </Label>
        <Label className="flex cursor-pointer space-x-2">
          <RadioGroupItem value="necc" id="competition-necc" />
          <span className="">NECC</span>
        </Label>
        <Label className="flex cursor-pointer space-x-2">
          <RadioGroupItem value="playfly" id="competition-playfly" />
          <span className="">Playfly</span>
        </Label>
      </RadioGroup>
    </div>
  );
}
