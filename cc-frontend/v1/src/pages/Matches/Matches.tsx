import { ArrowRight, Menu, Star } from "lucide-react";
import logo from "@/assets/0.1x/C Logo@0.1x.png";
import { useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { Spinner } from "@/components/ui/shadcn-io/spinner";
import { usePublicMatches, usePublicSeasons } from "@/services/hooks";
import InfiniteScroll from "react-infinite-scroll-component";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import type { PublicMatch, MatchQueryParams } from "@/services/api";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import Logo from "@/components/Logo";

function Matches() {
  const getInitialMatchType = () => {
    const hash = window.location.hash.replace("#", "");
    if (hash === "live" || hash === "upcoming" || hash === "past") {
      return hash;
    }
    return "upcoming";
  };

  const [matchType, setMatchType] = useState(getInitialMatchType() || "live");
  window.location.hash = matchType;

  return (
    <div className="app-container mx-4 flex justify-center">
      <div className="matches w-full max-w-[1000px]">
        <div className="flex justify-center">
          <div className="my-4 flex h-12 w-[500px] rounded-xl border-2">
            <div
              onClick={() => setMatchType("live")}
              className={`flex-2 group flex items-center justify-center rounded-lg ${matchType === "live" ? "bg-muted" : "cursor-pointer"}`}
            >
              <h2
                className={`transition-colors duration-200 ${
                  matchType === "live"
                    ? ""
                    : "text-muted-foreground group-hover:text-foreground"
                }`}
              >
                Live
              </h2>
            </div>
            <div
              onClick={() => setMatchType("upcoming")}
              className={`flex-3 group flex items-center justify-center rounded-lg ${matchType === "upcoming" ? "bg-muted" : "cursor-pointer"}`}
            >
              <h2
                className={`transition-colors duration-200 ${
                  matchType === "upcoming"
                    ? ""
                    : "text-muted-foreground group-hover:text-foreground"
                }`}
              >
                Upcoming
              </h2>
            </div>
            <div
              onClick={() => setMatchType("past")}
              className={`flex-2 group flex items-center justify-center rounded-lg ${matchType === "past" ? "bg-muted" : "cursor-pointer"}`}
            >
              <h2
                className={`transition-colors duration-200 ${
                  matchType === "past"
                    ? ""
                    : "text-muted-foreground group-hover:text-foreground"
                }`}
              >
                Past
              </h2>
            </div>
          </div>
        </div>
        {matchType === "upcoming" ? <Upcoming /> : null}
        {matchType === "live" ? <Live /> : null}
        {matchType === "past" ? <Past /> : null}
      </div>
    </div>
  );
}

export default Matches;

function Live() {
  return (
    <>
      <h1>Live Matches</h1>
      <hr />
      <ul className="mt-3 grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
        {Array.from({ length: 11 }).map((_, i) => (
          <LiveMatch key={i} />
        ))}
      </ul>
    </>
  );
}

function LiveMatch() {
  return (
    <li className="rounded-xl border-2 p-4 py-2">
      <div className="flex">
        <div className="flex-3 space-y-1">
          <div className="mb-2 flex items-center space-x-2">
            <img src={logo} className="h-6 w-6" alt="Logo" />
            <span className="truncate overflow-ellipsis whitespace-nowrap">
              Test University
            </span>
          </div>
          <div className="flex items-center space-x-2 overflow-ellipsis">
            <img src={logo} className="h-6 w-6" alt="Logo" />
            <span className="truncate overflow-ellipsis whitespace-nowrap">
              University of Test
            </span>
          </div>
        </div>
        <div className="flex-1 space-y-2 text-end">
          <span className="flex justify-end">
            <p className="font-mono text-green-500">11</p>
            <p className="bg-muted ml-2 rounded-sm px-1 font-mono text-red-500">
              0
            </p>
          </span>
          <span className="flex justify-end">
            <p className="font-mono text-red-500">4</p>
            <p className="bg-muted ml-2 rounded-sm px-1 font-mono text-green-500">
              1
            </p>
          </span>
        </div>
      </div>
      <Button className="bg-secondary text-foreground group mt-2 flex w-full cursor-pointer items-center">
        View
        <ArrowRight
          size={1}
          className="mt-0.5 transition-all group-hover:ml-2"
        />
      </Button>
    </li>
  );
}

function Upcoming() {
  return (
    <>
      <h1>Today</h1>
      <hr />
      <ul className="mt-3 grid grid-cols-1 gap-4 md:grid-cols-2">
        {Array.from({ length: 9 }).map((_, i) => (
          <UpcomingMatch key={i} />
        ))}
      </ul>
      <h1 className="mt-8">This Week</h1>
      <hr />
      <ul className="mt-3 grid grid-cols-1 gap-4 md:grid-cols-2">
        {Array.from({ length: 100 }).map((_, i) => (
          <UpcomingMatch key={i} />
        ))}
      </ul>
    </>
  );
}

function UpcomingMatch() {
  const stars = Math.floor(Math.random() * 5) + 1;
  return (
    <li
      className={`bg-background flex rounded-xl border-2 p-4 py-2 ${stars === 5 ? "drop-shadow-primary/40 border-primary drop-shadow-lg" : ""}`}
    >
      <div className="flex-3 space-y-3">
        <div className="flex items-center space-x-2">
          <img src={logo} className="h-6 w-6" alt="Logo" />
          <span className="truncate overflow-ellipsis whitespace-nowrap">
            Test University
          </span>
          <span className="bg-muted ml-2 flex items-center justify-end rounded-sm text-xs">
            <p className="border-r-1 px-1 font-mono text-xs text-green-500">
              +76
            </p>
            <p className="rounded-sm px-1 font-mono text-xs text-red-500">
              -23
            </p>
          </span>
        </div>
        <div className="flex items-center space-x-2 overflow-ellipsis">
          <img src={logo} className="h-6 w-6" alt="Logo" />
          <span className="truncate overflow-ellipsis whitespace-nowrap">
            University of Test
          </span>
          <span className="bg-muted ml-2 flex items-center justify-end rounded-sm text-xs">
            <p className="border-r-1 px-1 font-mono text-xs text-green-500">
              +23
            </p>
            <p className="rounded-sm px-1 font-mono text-xs text-red-500">
              -76
            </p>
          </span>
        </div>
      </div>
      <div className="flex-1 text-end text-sm">
        <span className="text-muted-foreground">2025-10-01</span>
        <br />
        <span className="text-muted-foreground">3:00 PM</span>
        <br />
        <span className="text-muted-foreground space-x-.5 mt-1 flex items-center justify-end">
          {Array.from({ length: stars }).map((_, i) => (
            <Star key={i} size={14} className="fill-muted-foreground" />
          ))}
          {Array.from({ length: 5 - stars }).map((_, i) => (
            <Star key={i} size={14} className="text-gray-700" />
          ))}
        </span>
      </div>
    </li>
  );
}

function Past() {
  const [isExpanded, setIsExpanded] = useState(false);
  const [page, setPage] = useState(1);
  const [matches, setMatches] = useState<PublicMatch[]>([]);
  const [hasMore, setHasMore] = useState(true);
  const [filters, setFilters] = useState<MatchQueryParams>({
    date_from: "",
    date_to: "",
    season_id: "",
    competition_name: "",
    sort: "date",
    order: "desc",
    status: "completed",
  });

  // Apply filters to the query
  const { data, isLoading, error } = usePublicMatches(
    {
      page,
      page_size: 30,
      status: "completed",
      ...filters,
    },
    {
      staleTime: 1000 * 60 * 5,
      keepPreviousData: true,
    },
  );

  // Update matches when data changes
  useEffect(() => {
    if (data?.results) {
      setMatches((prevMatches) =>
        page === 1 ? data.results : [...prevMatches, ...data.results],
      );
      setHasMore(data.results.length > 0 && data.results.length === 30);
    }
  }, [data, page]);

  // Don't use a useEffect for filter changes - handle it directly in the change handler

  const loadMoreMatches = () => {
    if (!isLoading && hasMore) {
      setPage((prevPage) => prevPage + 1);
    }
  };

  const handleFilterChange = (newFilters: Partial<typeof filters>) => {
    // Reset page and matches when filters change, and then update filters
    setPage(1);
    setMatches([]);
    setFilters((prev) => ({ ...prev, ...newFilters }));
  };

  if (error) {
    return (
      <Alert variant="destructive" className="mt-4">
        <AlertTitle className="text-lg">Error</AlertTitle>
        <AlertDescription>
          There was an error loading the match history. Please try again later.
        </AlertDescription>
      </Alert>
    );
  }

  return (
    <>
      <div className="mb-2 flex flex-col md:flex-row md:items-start md:justify-between">
        <div className="w-full">
          <h1 className="">Past Matches</h1>
          <hr />
        </div>
      </div>

      <div
        className={`matches-filter mt-4 w-full cursor-pointer rounded-xl border-2 p-4 md:mt-0 md:w-auto ${isExpanded ? "max-h-[1000px]" : "max-h-16"} transition-all duration-300`}
        onClick={() => setIsExpanded(!isExpanded)}
      >
        <div className="mb-2 flex items-center justify-between">
          <h2 className="font-semibold">Filter Matches</h2>

          <Menu />
        </div>
        <div
          className={`bg-background z-10 transition-all duration-200 ${isExpanded ? "opacity-100" : "pointer-events-none opacity-0"}`}
        >
          <MatchesFilter
            filters={filters}
            onFilterChange={handleFilterChange}
          />
        </div>
      </div>

      <InfiniteScroll
        dataLength={matches.length}
        hasMore={hasMore}
        next={loadMoreMatches}
        loader={
          <div className="flex h-10 justify-center">
            <Spinner />
          </div>
        }
        endMessage={
          <div className="text-muted-foreground my-4 text-center">
            No more matches to load
          </div>
        }
        className="infinite-scroll-container"
      >
        <ul className="mt-3 grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
          {matches.map((match, i) => (
            <Result key={match.id || i} match={match} />
          ))}
        </ul>
      </InfiniteScroll>
    </>
  );
}

interface ResultProps {
  match: PublicMatch;
}

function Result(props: ResultProps) {
  const winningTeamId = props.match.winner?.id;
  let winner, loser;
  if (winningTeamId === props.match.team1.id) {
    winner = props.match.team1;
    loser = props.match.team2;
  } else {
    winner = props.match.team2;
    loser = props.match.team1;
  }

  return (
    <li className="cursor-pointer rounded-xl border-2 p-4 py-2">
      <div className="flex">
        <div className="flex-3 space-y-2">
          <div className="flex items-center space-x-2">
            <Logo
              src={winner.picture}
              className="h-6 w-6"
              alt="pfp"
              type="team"
            />
            <span className="truncate overflow-ellipsis whitespace-nowrap font-semibold">
              {winner.name}
            </span>
            <span className="flex justify-end">
              <p className="ml-2 rounded-sm px-1 font-mono text-xs text-green-500">
                {/* TODO: INCLUDE +- ELO FROM RESULTS */}
              </p>
            </span>
          </div>
          <div className="flex items-center space-x-2 overflow-ellipsis">
            <Logo
              src={loser.picture || logo}
              className="h-6 w-6"
              alt="pfp"
              type="team"
            />
            <span className="text-muted-foreground truncate overflow-ellipsis whitespace-nowrap">
              {loser.name}
            </span>
            <span className="flex justify-end">
              <p className="ml-2 rounded-sm px-1 font-mono text-xs text-red-500">
                {/* TODO: INCLUDE +- ELO FROM RESULTS */}
              </p>
            </span>
          </div>
        </div>
        <div className="flex-1 space-y-2 text-end">
          <span className="flex justify-end">
            <p className="bg-muted ml-2 rounded-sm px-1 font-mono text-green-500">
              {Math.max(props.match.score_team1, props.match.score_team2)}
            </p>
          </span>
          <span className="flex justify-end">
            <p className="bg-muted ml-2 rounded-sm px-1 font-mono text-red-500">
              {Math.min(props.match.score_team1, props.match.score_team2)}
            </p>
          </span>
        </div>
      </div>
      <hr className="my-2" />
      <div className="flex items-end justify-between">
        <div className="flex items-center space-x-2">
          <div className="bg-secondary rounded-sm px-1 py-0.5">
            {props.match.competition?.name || ""}
          </div>
          <div className="bg-muted rounded-sm px-1 py-0.5">
            {props.match.season?.name || ""}
          </div>
        </div>
        <p className="text-muted-foreground py-0.5">
          {new Date(props.match.date).toLocaleString(undefined, {
            year: "numeric",
            month: "short",
            day: "numeric",
          })}
        </p>
      </div>
    </li>
  );
}

interface MatchesFilterProps {
  filters: MatchQueryParams;
  onFilterChange: (filters: Partial<MatchQueryParams>) => void;
}

function MatchesFilter({ filters, onFilterChange }: MatchesFilterProps) {
  const { data: seasonsData, isLoading } = usePublicSeasons();
  const seasons = seasonsData?.results || [];

  if (isLoading) {
    return (
      <div className="matches-filter mt-4 w-full rounded-xl border-2 p-4 md:mt-0 md:w-auto">
        <Spinner className="mx-auto my-4" />
      </div>
    );
  }

  return (
    <div className={`mt-4 flex flex-wrap space-x-2 space-y-2`}>
      <div className="space-y-1">
        <Label htmlFor="date-from">From Date</Label>
        <Input
          id="date-from"
          type="date"
          value={filters.date_from || ""}
          onChange={(e) => onFilterChange({ date_from: e.target.value })}
          className="w-full"
        />
      </div>
      <div className="space-y-1">
        <Label htmlFor="date-to">To Date</Label>
        <Input
          id="date-to"
          type="date"
          value={filters.date_to || ""}
          onChange={(e) => onFilterChange({ date_to: e.target.value })}
          className="w-full"
        />
      </div>

      <div className="space-y-1">
        <Label htmlFor="season">Season</Label>
        <Select
          value={filters.season_id || "all_seasons"}
          onValueChange={(value) =>
            onFilterChange({
              season_id: value === "all_seasons" ? "" : value,
            })
          }
        >
          <SelectTrigger id="season">
            <SelectValue placeholder="Select a season" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all_seasons">All Seasons</SelectItem>
            {seasons.map((season) => (
              <SelectItem key={season.id} value={season.id}>
                {season.name}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      <div className="space-y-1">
        <Label htmlFor="competition">Competition</Label>
        <Select
          value={filters.competition_name || "all_competitions"}
          onValueChange={(value) =>
            onFilterChange({
              competition_name: value === "all_competitions" ? "" : value,
            })
          }
        >
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
        <Label htmlFor="order">Order</Label>
        <Select
          value={filters.order || "desc"}
          onValueChange={(value: "asc" | "desc") =>
            onFilterChange({ order: value })
          }
        >
          <SelectTrigger id="order">
            <SelectValue placeholder="Order" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="desc">Newest First</SelectItem>
            <SelectItem value="asc">Oldest First</SelectItem>
          </SelectContent>
        </Select>
      </div>
      <div className="space-y-1">
        <Label className="invisible">Reset</Label>
        <Button
          onClick={() =>
            onFilterChange({
              date_from: "",
              date_to: "",
              season_id: "",
              competition_name: "",
              sort: "date",
              order: "desc",
            })
          }
          variant="destructive"
          className="cursor-pointer"
        >
          Reset Filters
        </Button>
      </div>
    </div>
  );
}
