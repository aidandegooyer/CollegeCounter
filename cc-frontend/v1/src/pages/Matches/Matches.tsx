import {
  ArrowRight,
  ChevronDown,
  SlidersHorizontal,
  Star,
  X,
} from "lucide-react";
import React, { useEffect, useMemo, useState } from "react";
import { Button } from "@/components/ui/button";
import { Spinner } from "@/components/ui/shadcn-io/spinner";
import {
  useAllPublicMatches,
  useInfinitePublicMatches,
  usePublicCompetitions,
  usePublicMatches,
  usePublicSeasons,
} from "@/services/hooks";
import InfiniteScroll from "react-infinite-scroll-component";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import type { PublicMatch } from "@/services/api";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Checkbox } from "@/components/ui/checkbox";
import { Badge } from "@/components/ui/badge";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";
import Logo from "@/components/Logo";
import { calculateEloChanges, calculateMatchStars } from "@/services/elo";
import { NavLink, useLocation, useNavigate } from "react-router";
import { CompetitionLabel } from "@/components/CompetitionLabel";

function Matches() {
  // The selected tab lives in the hash, so back/forward switch tabs
  const location = useLocation();
  const navigate = useNavigate();
  const hash = location.hash.replace("#", "");
  const matchType =
    hash === "live" || hash === "upcoming" || hash === "past"
      ? hash
      : "upcoming";
  const setMatchType = (tab: typeof matchType) => {
    // Each tab has its own filters, so don't carry them over
    if (tab !== matchType) navigate({ hash: tab });
  };
  document.title = "Matches - College Counter";

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
  const {
    data: liveMatches,
    isLoading,
    error,
  } = usePublicMatches({
    status: "in_progress",
    sort: "date",
    order: "desc",
  });

  if (error) {
    return (
      <Alert variant="destructive" className="mt-4">
        <AlertTitle className="text-lg">Error</AlertTitle>
        <AlertDescription>
          There was an error loading live matches. Please try again later.
        </AlertDescription>
      </Alert>
    );
  }

  return (
    <>
      <h1>Live Matches</h1>
      <hr />
      {isLoading ? (
        <div className="flex h-20 items-center justify-center">
          <Spinner />
        </div>
      ) : liveMatches?.results && liveMatches.results.length > 0 ? (
        <ul className="mt-3 grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
          {liveMatches.results.map((match) => (
            <LiveMatch key={match.id} match={match} />
          ))}
        </ul>
      ) : (
        <div className="text-muted-foreground my-4 text-center">
          No live matches currently
        </div>
      )}
    </>
  );
}

interface LiveMatchProps {
  match: PublicMatch;
}

function LiveMatch({ match }: LiveMatchProps) {
  const useableUrl = match.url?.replace("{lang}", "en");
  return (
    <li className="rounded-xl border-2 p-4 py-2">
      <div className="flex">
        <div className="flex-3 space-y-1">
          <div className="mb-2 flex items-center space-x-2">
            <Logo src={match.team1?.picture} type="team" className="h-6 w-6" />
            <span className="truncate overflow-ellipsis whitespace-nowrap">
              {match.team1?.name || "Unknown Team"}
            </span>
          </div>
          <div className="flex items-center space-x-2 overflow-ellipsis">
            <Logo src={match.team2?.picture} type="team" className="h-6 w-6" />
            <span className="truncate overflow-ellipsis whitespace-nowrap">
              {match.team2?.name || "Unknown Team"}
            </span>
          </div>
        </div>
        <div className="flex-1 space-y-2 text-end">
          <span className="flex justify-end">
            <p
              className={`font-mono ${match.score_team1 > match.score_team2 ? "text-green-500" : "text-red-500"}`}
            >
              {match.score_team1}
            </p>
          </span>
          <span className="flex justify-end">
            <p
              className={`font-mono ${match.score_team2 > match.score_team1 ? "text-green-500" : "text-red-500"}`}
            >
              {match.score_team2}
            </p>
          </span>
        </div>
      </div>
      {match.url && (
        <Button
          className="text-foreground group mt-2 flex w-full cursor-pointer items-center"
          variant="secondary"
          asChild
        >
          <NavLink to={match.id ? `/matches/${match.id}` : useableUrl || "#"}>
            View
            <ArrowRight
              size={16}
              className="ml-1 transition-all group-hover:ml-2"
            />
          </NavLink>
        </Button>
      )}
    </li>
  );
}

// Filters live in the URL so they survive a refresh and can be shared
function useUrlSearchParams() {
  const location = useLocation();
  const navigate = useNavigate();
  const searchParams = new URLSearchParams(location.search);

  const update = (mutate: (params: URLSearchParams) => void) => {
    const params = new URLSearchParams(location.search);
    mutate(params);
    const search = params.toString();
    // Keep the hash, which holds the selected Live/Upcoming/Past tab
    navigate(
      { search: search ? `?${search}` : "", hash: location.hash },
      { replace: true },
    );
  };

  return [searchParams, update] as const;
}

interface FilterChip {
  label: string;
  onRemove: () => void;
}

interface FilterBarProps {
  chips: FilterChip[];
  onClearAll: () => void;
  children: React.ReactNode;
}

// Shared shell for the Upcoming and Past filters: controls, then a row of
// removable chips for whatever is active. On mobile the controls collapse
// behind the header (chips stay visible); on desktop they're always shown.
function FilterBar({ chips, onClearAll, children }: FilterBarProps) {
  const [isOpen, setIsOpen] = useState(false);

  return (
    <div className="mt-4 rounded-xl border-2 p-4">
      <h2 className="text-base">
        <button
          type="button"
          aria-expanded={isOpen}
          onClick={() => setIsOpen(!isOpen)}
          className="flex w-full cursor-pointer items-center gap-2 md:pointer-events-none md:cursor-default"
        >
          <SlidersHorizontal className="text-muted-foreground size-4" />
          Filter matches
          {chips.length > 0 && (
            <Badge className="md:hidden">{chips.length}</Badge>
          )}
          <ChevronDown
            className={`text-muted-foreground ml-auto size-4 transition-transform md:hidden ${isOpen ? "rotate-180" : ""}`}
          />
        </button>
      </h2>
      <div className={`mt-3 ${isOpen ? "" : "hidden md:block"}`}>
        {children}
      </div>
      {chips.length > 0 && (
        <div className="mt-3 flex flex-wrap items-center gap-2">
          {chips.map((chip) => (
            <Badge key={chip.label} variant="secondary" className="py-1 pl-2.5">
              {chip.label}
              <button
                type="button"
                aria-label={`Remove ${chip.label} filter`}
                className="hover:text-foreground text-muted-foreground cursor-pointer"
                onClick={chip.onRemove}
              >
                <X className="size-3" />
              </button>
            </Badge>
          ))}
          <Button
            variant="link"
            size="sm"
            className="text-muted-foreground h-auto cursor-pointer px-1"
            onClick={onClearAll}
          >
            Clear all
          </Button>
        </div>
      )}
    </div>
  );
}

// Local YYYY-MM-DD, since the API treats bare dates as whole days
function toDateParam(date: Date) {
  return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, "0")}-${String(date.getDate()).padStart(2, "0")}`;
}

function endOfDay(date: Date, daysAhead = 0) {
  const end = new Date(date);
  end.setDate(end.getDate() + daysAhead);
  end.setHours(23, 59, 59, 999);
  return end;
}

function useUpcomingFilters() {
  const [searchParams, updateSearchParams] = useUrlSearchParams();
  const competitions = searchParams.getAll("competition");
  const minStars = Math.min(
    Math.max(Number(searchParams.get("min_stars")) || 0, 0),
    5,
  );

  const setCompetitions = (names: string[]) =>
    updateSearchParams((params) => {
      params.delete("competition");
      names.forEach((name) => params.append("competition", name));
    });
  const setMinStars = (stars: number) =>
    updateSearchParams((params) => {
      if (stars > 0) params.set("min_stars", String(stars));
      else params.delete("min_stars");
    });

  return { competitions, minStars, setCompetitions, setMinStars };
}

interface RatedMatch {
  match: PublicMatch;
  stars: number;
}

function Upcoming() {
  const { competitions, minStars, setCompetitions, setMinStars } =
    useUpcomingFilters();

  // Fixed for the life of the page so the day buckets and query stay stable
  const [now] = useState(() => new Date());

  const {
    data: allMatches,
    isLoading,
    error,
  } = useAllPublicMatches({
    date_from: toDateParam(now),
    date_to: toDateParam(endOfDay(now, 30)),
    status: "scheduled",
    sort: "date",
    order: "asc",
  });

  const { ratedMatches, availableCompetitions } = useMemo(() => {
    const ratedMatches: RatedMatch[] = (allMatches ?? []).map((match) => ({
      match,
      stars: calculateMatchStars(
        match.team1?.elo || 1000,
        match.team2?.elo || 1000,
      ),
    }));

    // Deduplicate by name, since re-imported competitions share one
    const names = new Map<string, string>();
    for (const { match } of ratedMatches) {
      const name = match.competition?.name?.trim();
      if (name && !names.has(name.toLowerCase())) {
        names.set(name.toLowerCase(), name);
      }
    }

    return {
      ratedMatches,
      availableCompetitions: [...names.values()].sort((a, b) =>
        a.localeCompare(b),
      ),
    };
  }, [allMatches]);

  const sections = useMemo(() => {
    const selected = new Set(competitions.map((c) => c.toLowerCase()));
    const visible = ratedMatches
      .filter(
        ({ match, stars }) =>
          stars >= minStars &&
          (selected.size === 0 ||
            selected.has(match.competition?.name?.trim().toLowerCase() ?? "")),
      )
      // Earliest first, then highest stars, then highest combined ELO
      .sort(
        (a, b) =>
          new Date(a.match.date || 0).getTime() -
            new Date(b.match.date || 0).getTime() ||
          b.stars - a.stars ||
          (b.match.team1.elo || 1000) +
            (b.match.team2.elo || 1000) -
            ((a.match.team1.elo || 1000) + (a.match.team2.elo || 1000)),
      );

    const buckets = [
      { title: "Today", empty: "today", end: endOfDay(now) },
      { title: "Tomorrow", empty: "tomorrow", end: endOfDay(now, 1) },
      { title: "This Week", empty: "this week", end: endOfDay(now, 7) },
      { title: "This Month", empty: "this month", end: endOfDay(now, 30) },
    ].map((bucket) => ({ ...bucket, matches: [] as RatedMatch[] }));

    for (const rated of visible) {
      const date = new Date(rated.match.date || 0);
      buckets.find((bucket) => date <= bucket.end)?.matches.push(rated);
    }
    return buckets;
  }, [ratedMatches, competitions, minStars, now]);

  if (error) {
    return (
      <Alert variant="destructive" className="mt-4">
        <AlertTitle className="text-lg">Error</AlertTitle>
        <AlertDescription>
          There was an error loading upcoming matches. Please try again later.
        </AlertDescription>
      </Alert>
    );
  }

  const chips: FilterChip[] = competitions.map((name) => ({
    label: name,
    onRemove: () => setCompetitions(competitions.filter((c) => c !== name)),
  }));
  if (minStars > 0) {
    chips.push({
      label: `${minStars}+ stars`,
      onRemove: () => setMinStars(0),
    });
  }

  return (
    <>
      <div className="mb-2">
        <h1>Upcoming Matches</h1>
        <hr />
      </div>

      <FilterBar
        chips={chips}
        onClearAll={() => {
          setCompetitions([]);
          setMinStars(0);
        }}
      >
        <div className="flex flex-col gap-3 md:flex-row md:items-end">
          <div className="space-y-1 md:w-64">
            <Label htmlFor="upcoming-competitions">Competitions</Label>
            <CompetitionMultiSelect
              id="upcoming-competitions"
              options={availableCompetitions}
              selected={competitions}
              onChange={setCompetitions}
            />
          </div>
          <div className="space-y-1">
            <Label>Minimum stars</Label>
            <div className="flex flex-wrap gap-1">
              {[0, 1, 2, 3, 4, 5].map((stars) => (
                <button
                  key={stars}
                  type="button"
                  aria-pressed={minStars === stars}
                  onClick={() => setMinStars(stars)}
                  className={`flex h-9 cursor-pointer items-center gap-1 rounded-md px-3 text-sm transition-colors ${
                    minStars === stars
                      ? "bg-primary text-primary-foreground"
                      : "bg-muted text-muted-foreground hover:bg-muted/80"
                  }`}
                >
                  {stars === 0 ? (
                    "Any"
                  ) : (
                    <>
                      {stars}+
                      <Star size={12} className="fill-current" />
                    </>
                  )}
                </button>
              ))}
            </div>
          </div>
        </div>
      </FilterBar>

      {sections.map((section, i) => (
        <section key={section.title} className={i === 0 ? "mt-6" : "mt-8"}>
          <h2 className="font-block text-3xl font-normal">{section.title}</h2>
          <hr />
          {isLoading ? (
            <div className="flex h-20 items-center justify-center">
              <Spinner />
            </div>
          ) : section.matches.length > 0 ? (
            <ul className="mt-3 grid grid-cols-1 gap-4 lg:grid-cols-2">
              {section.matches.map(({ match, stars }) => (
                <UpcomingMatch key={match.id} match={match} stars={stars} />
              ))}
            </ul>
          ) : (
            <div className="text-muted-foreground my-4 text-center">
              {chips.length > 0
                ? `No matches ${section.empty} match these filters`
                : `No matches scheduled for ${section.empty}`}
            </div>
          )}
        </section>
      ))}
    </>
  );
}

interface CompetitionMultiSelectProps {
  id: string;
  options: string[];
  selected: string[];
  onChange: (selected: string[]) => void;
}

function CompetitionMultiSelect({
  id,
  options,
  selected,
  onChange,
}: CompetitionMultiSelectProps) {
  const isSelected = (name: string) =>
    selected.some((s) => s.toLowerCase() === name.toLowerCase());
  const toggle = (name: string) =>
    onChange(
      isSelected(name)
        ? selected.filter((s) => s.toLowerCase() !== name.toLowerCase())
        : [...selected, name],
    );

  const label =
    selected.length === 0
      ? "All competitions"
      : selected.length === 1
        ? selected[0]
        : `${selected.length} competitions`;

  return (
    <Popover>
      <PopoverTrigger asChild>
        <Button
          id={id}
          variant="outline"
          className="w-full cursor-pointer justify-between font-normal"
        >
          <span className="truncate">{label}</span>
          <ChevronDown className="text-muted-foreground size-4" />
        </Button>
      </PopoverTrigger>
      <PopoverContent align="start" className="w-64 p-1">
        {options.length === 0 ? (
          <p className="text-muted-foreground p-2 text-sm">
            No upcoming competitions
          </p>
        ) : (
          <ul className="max-h-72 overflow-y-auto">
            {options.map((name) => (
              <li key={name}>
                <label className="hover:bg-muted flex cursor-pointer items-center gap-2 rounded-sm px-2 py-1.5 text-sm">
                  <Checkbox
                    checked={isSelected(name)}
                    onCheckedChange={() => toggle(name)}
                  />
                  {name}
                </label>
              </li>
            ))}
          </ul>
        )}
      </PopoverContent>
    </Popover>
  );
}

interface UpcomingMatchProps {
  match: PublicMatch;
  stars: number;
}

function UpcomingMatch({ match, stars }: UpcomingMatchProps) {
  const changes_team1 = calculateEloChanges(
    match.team1?.elo || 1000,
    match.team2?.elo || 1000,
  );
  const changes_team2 = calculateEloChanges(
    match.team2?.elo || 1000,
    match.team1?.elo || 1000,
  );
  // Format date and time
  const matchDate = new Date(match.date || "");
  const dateStr = matchDate.toLocaleDateString([], {
    day: "numeric",
    month: "short",
  });
  const timeStr = matchDate.toLocaleTimeString([], {
    hour: "numeric",
    minute: "2-digit",
  });
  const navigate = useNavigate();

  const handleClick = () => {
    navigate(`/matches/${match.id}`);
  };

  return (
    <li
      className={`bg-background flex cursor-pointer rounded-xl border-2 p-4 py-2 ${stars === 5 ? "drop-shadow-primary/40 border-primary drop-shadow-lg" : ""} ${match.competition?.name === "c4" || match.competition?.name === "C4" ? "drop-shadow-secondary/40 border-secondary drop-shadow-lg" : ""} transition-all`}
      onClick={handleClick}
    >
      <div className="sm:flex-5 my-auto flex-1 space-y-3">
        <div className="flex items-center space-x-2">
          <Logo src={match.team1?.picture} type="team" className="h-6 w-6" />
          <span className="truncate overflow-ellipsis whitespace-nowrap">
            {match.team1?.name || "Unknown Team"}
          </span>
          <span className="ml-2 hidden items-center justify-end text-xs sm:flex">
            <div className="text-muted-foreground bg-muted flex rounded-sm px-1 font-mono text-xs">
              <div className="text-muted-foreground border-r-2 pr-1 font-mono">
                {match.team1?.elo}
              </div>
              <div className="border-r-2 border-dotted px-1 font-mono text-green-600">
                {changes_team1.winChange >= 0
                  ? `+${changes_team1.winChange}`
                  : changes_team1.winChange}
              </div>
              <div className="border-foreground-muted pl-1 font-mono text-red-600">
                {changes_team1.lossChange >= 0
                  ? `+${changes_team1.lossChange}`
                  : changes_team1.lossChange}
              </div>
            </div>
          </span>
        </div>
        <div className="flex items-center space-x-2 overflow-ellipsis">
          <Logo src={match.team2?.picture} type="team" className="h-6 w-6" />
          <span className="truncate overflow-ellipsis whitespace-nowrap">
            {match.team2?.name || "Unknown Team"}
          </span>
          <span className="ml-2 hidden items-center justify-end text-xs sm:flex">
            <div className="text-muted-foreground bg-muted flex rounded-sm px-1 font-mono text-xs">
              <div className="text-muted-foreground border-r-2 pr-1 font-mono">
                {match.team2?.elo}
              </div>
              <div className="border-r-2 border-dotted px-1 font-mono text-green-600">
                {changes_team2.winChange >= 0
                  ? `+${changes_team2.winChange}`
                  : changes_team2.winChange}
              </div>
              <div className="border-foreground-muted pl-1 font-mono text-red-600">
                {changes_team2.lossChange >= 0
                  ? `+${changes_team2.lossChange}`
                  : changes_team2.lossChange}
              </div>
            </div>
          </span>
        </div>
      </div>
      <div className="sm:flex-2 flex-1 text-end text-sm">
        <span className="text-muted-foreground">
          {dateStr}, {timeStr}
        </span>
        <br />
        <span className="flex justify-end">
          {match.competition?.name && (
            <CompetitionLabel
              competition={match.competition.name}
              h={12}
              w={18}
            />
          )}
        </span>
        {match.competition?.name != "c4" && match.competition?.name != "C4" && (
          <span className="text-muted-foreground space-x-.5 mt-1 flex items-center justify-end">
            {Array.from({ length: stars }).map((_, i) => (
              <Star key={i} size={14} className="fill-muted-foreground" />
            ))}
            {Array.from({ length: 5 - stars }).map((_, i) => (
              <Star key={i} size={14} className="text-gray-700" />
            ))}
          </span>
        )}
      </div>
    </li>
  );
}

interface PastFilters {
  season_id: string;
  competition_name: string;
  date_from: string;
  date_to: string;
  order: "asc" | "desc";
}

const PAST_FILTER_DEFAULTS: PastFilters = {
  season_id: "",
  competition_name: "",
  date_from: "",
  date_to: "",
  order: "desc",
};

const PAST_FILTER_KEYS = Object.keys(PAST_FILTER_DEFAULTS) as Array<
  keyof PastFilters
>;

function usePastFilters() {
  const [searchParams, updateSearchParams] = useUrlSearchParams();

  const filters: PastFilters = {
    season_id: searchParams.get("season_id") ?? "",
    competition_name: searchParams.get("competition_name") ?? "",
    date_from: searchParams.get("date_from") ?? "",
    date_to: searchParams.get("date_to") ?? "",
    order: searchParams.get("order") === "asc" ? "asc" : "desc",
  };

  const setFilters = (changes: Partial<PastFilters>) => {
    const next = { ...filters, ...changes };
    updateSearchParams((params) => {
      for (const key of PAST_FILTER_KEYS) {
        if (next[key] && next[key] !== PAST_FILTER_DEFAULTS[key]) {
          params.set(key, next[key]);
        } else {
          params.delete(key);
        }
      }
    });
  };

  return [filters, setFilters] as const;
}

function Past() {
  const [filters, setFilters] = usePastFilters();

  const {
    data,
    error,
    isLoading,
    isFetching,
    isFetchingNextPage,
    isPlaceholderData,
    hasNextPage,
    fetchNextPage,
  } = useInfinitePublicMatches({
    page_size: 30,
    status: "completed",
    sort: "date",
    ...filters,
  });

  const matches = data?.pages.flatMap((page) => page.results) ?? [];
  const total = data?.pages[0]?.count ?? 0;
  const hasActiveFilters = PAST_FILTER_KEYS.some(
    (key) => key !== "order" && filters[key],
  );

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
      <div className="mb-2">
        <h1>Past Matches</h1>
        <hr />
      </div>

      <MatchesFilter filters={filters} onFilterChange={setFilters} />

      <div className="text-muted-foreground mt-4 flex h-6 items-center justify-between text-sm">
        <span>
          {isLoading ? "" : `${total} ${total === 1 ? "match" : "matches"}`}
        </span>
        {isFetching && !isFetchingNextPage && !isLoading && (
          <Spinner className="h-4 w-4" />
        )}
      </div>

      {isLoading ? (
        <div className="flex h-24 items-center justify-center">
          <Spinner />
        </div>
      ) : matches.length === 0 ? (
        <div className="text-muted-foreground my-10 flex flex-col items-center gap-3 text-center">
          <p>No matches found for these filters.</p>
          {hasActiveFilters && (
            <Button
              variant="outline"
              className="cursor-pointer"
              onClick={() => setFilters(PAST_FILTER_DEFAULTS)}
            >
              Clear filters
            </Button>
          )}
        </div>
      ) : (
        <InfiniteScroll
          dataLength={matches.length}
          hasMore={!!hasNextPage}
          next={() => {
            if (!isFetching) fetchNextPage();
          }}
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
          <ul
            className={`mt-2 grid grid-cols-1 gap-4 transition-opacity md:grid-cols-2 lg:grid-cols-3 ${isPlaceholderData ? "opacity-50" : ""}`}
          >
            {matches.map((match) => (
              <Result key={match.id} match={match} />
            ))}
          </ul>
        </InfiniteScroll>
      )}
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

  const navigate = useNavigate();

  const handleClick = () => {
    navigate(`/matches/${props.match.id}`);
  };

  return (
    <li
      className="cursor-pointer rounded-xl border-2 p-4 py-2"
      onClick={handleClick}
    >
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
              src={loser.picture}
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
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-2">
          {props.match.competition?.name && (
            <CompetitionLabel competition={props.match.competition.name} />
          )}
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
  filters: PastFilters;
  onFilterChange: (filters: Partial<PastFilters>) => void;
}

function MatchesFilter({ filters, onFilterChange }: MatchesFilterProps) {
  const { data: seasonsData } = usePublicSeasons({ page_size: 100 });
  const seasons = seasonsData?.results ?? [];
  const { data: competitionsData } = usePublicCompetitions(
    filters.season_id ? { season_id: filters.season_id } : {},
  );
  const competitions = (competitionsData?.results ?? []).map((c) => c.name);
  // Keep a selected competition visible even if the season has none by that name
  if (
    filters.competition_name &&
    !competitions.some(
      (name) => name.toLowerCase() === filters.competition_name.toLowerCase(),
    )
  ) {
    competitions.unshift(filters.competition_name);
  }

  const seasonName = seasons.find((s) => s.id === filters.season_id)?.name;
  const chips: FilterChip[] = [];
  if (filters.season_id) {
    chips.push({
      label: `Season: ${seasonName ?? "…"}`,
      onRemove: () => onFilterChange({ season_id: "" }),
    });
  }
  if (filters.competition_name) {
    chips.push({
      label: filters.competition_name,
      onRemove: () => onFilterChange({ competition_name: "" }),
    });
  }
  if (filters.date_from || filters.date_to) {
    chips.push({
      label: formatDateRange(filters.date_from, filters.date_to),
      onRemove: () => onFilterChange({ date_from: "", date_to: "" }),
    });
  }

  return (
    <FilterBar
      chips={chips}
      onClearAll={() =>
        onFilterChange({
          season_id: "",
          competition_name: "",
          date_from: "",
          date_to: "",
        })
      }
    >
      <div className="grid grid-cols-2 gap-3 md:grid-cols-5">
        <div className="col-span-2 space-y-1 md:col-span-1">
          <Label htmlFor="season">Season</Label>
          <Select
            value={filters.season_id || ALL}
            onValueChange={(value) =>
              onFilterChange({ season_id: value === ALL ? "" : value })
            }
          >
            <SelectTrigger id="season" className="w-full cursor-pointer">
              <SelectValue placeholder="All seasons" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value={ALL}>All seasons</SelectItem>
              {seasons.map((season) => (
                <SelectItem key={season.id} value={season.id}>
                  {season.name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        <div className="col-span-2 space-y-1 md:col-span-1">
          <Label htmlFor="competition">Competition</Label>
          <Select
            value={filters.competition_name || ALL}
            onValueChange={(value) =>
              onFilterChange({ competition_name: value === ALL ? "" : value })
            }
          >
            <SelectTrigger id="competition" className="w-full cursor-pointer">
              <SelectValue placeholder="All competitions" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value={ALL}>All competitions</SelectItem>
              {competitions.map((name) => (
                <SelectItem key={name} value={name}>
                  {name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        <DateFilterInput
          id="date-from"
          label="From"
          value={filters.date_from}
          max={filters.date_to || undefined}
          onCommit={(date_from) => onFilterChange({ date_from })}
        />
        <DateFilterInput
          id="date-to"
          label="To"
          value={filters.date_to}
          min={filters.date_from || undefined}
          onCommit={(date_to) => onFilterChange({ date_to })}
        />

        <div className="col-span-2 space-y-1 md:col-span-1">
          <Label htmlFor="order">Sort</Label>
          <Select
            value={filters.order}
            onValueChange={(value: "asc" | "desc") =>
              onFilterChange({ order: value })
            }
          >
            <SelectTrigger id="order" className="w-full cursor-pointer">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="desc">Newest first</SelectItem>
              <SelectItem value="asc">Oldest first</SelectItem>
            </SelectContent>
          </Select>
        </div>
      </div>
    </FilterBar>
  );
}

// Radix Select can't use "" as an item value
const ALL = "all";

interface DateFilterInputProps {
  id: string;
  label: string;
  value: string;
  min?: string;
  max?: string;
  onCommit: (value: string) => void;
}

// Native date inputs fire onChange while the year is still being typed
// (0002, 0020, 0202, 2025), so only commit complete dates or on blur
function DateFilterInput({
  id,
  label,
  value,
  min,
  max,
  onCommit,
}: DateFilterInputProps) {
  const [draft, setDraft] = useState(value);
  useEffect(() => setDraft(value), [value]);

  const isComplete = (date: string) =>
    date === "" || Number(date.slice(0, 4)) >= 2000;
  const commit = (next: string) => {
    if (next !== value) onCommit(next);
  };

  return (
    <div className="space-y-1">
      <Label htmlFor={id}>{label}</Label>
      <Input
        id={id}
        type="date"
        value={draft}
        min={min}
        max={max}
        onChange={(e) => {
          const next = e.target.value;
          setDraft(next);
          if (isComplete(next)) commit(next);
        }}
        onBlur={() => (isComplete(draft) ? commit(draft) : setDraft(value))}
        className="w-full"
      />
    </div>
  );
}

function formatDateRange(from: string, to: string) {
  // Parse as local dates so the label doesn't shift a day in US time zones
  const format = (date: string) =>
    new Date(`${date}T00:00:00`).toLocaleDateString(undefined, {
      year: "numeric",
      month: "short",
      day: "numeric",
    });
  if (from && to) return `${format(from)} – ${format(to)}`;
  if (from) return `From ${format(from)}`;
  return `Until ${format(to)}`;
}
