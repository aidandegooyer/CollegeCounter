import { ArrowRight, Menu, Star } from "lucide-react";
import React, { useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { Spinner } from "@/components/ui/shadcn-io/spinner";
import {
  usePublicMatches,
  usePublicSeasons,
  usePublicCompetitions,
} from "@/services/hooks";
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
import { Checkbox } from "@/components/ui/checkbox";
import Logo from "@/components/Logo";
import { calculateEloChanges, calculateMatchStars } from "@/services/elo";
import { NavLink, useNavigate } from "react-router";
import { CompetitionLabel } from "@/components/CompetitionLabel";

function Matches() {
  const getInitialMatchType = () => {
    const hash = window.location.hash.replace("#", "");
    if (hash === "live" || hash === "upcoming" || hash === "past") {
      return hash;
    }
    return "upcoming";
  };

  const [matchType, setMatchType] = useState(getInitialMatchType() || "live");
  useEffect(() => {
    window.location.hash = matchType;
  }, [matchType]);
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

function Upcoming() {
  // Competition filter state
  const [selectedCompetitions, setSelectedCompetitions] = useState<string[]>(
    [],
  );
  const [minStarCount, setMinStarCount] = useState<number>(0);
  const [isFilterExpanded, setIsFilterExpanded] = useState(false);

  // Get upcoming matches for today (using local timezone)
  const today = new Date();
  // Format date in local timezone as YYYY-MM-DD
  const todayStr = `${today.getFullYear()}-${String(today.getMonth() + 1).padStart(2, "0")}-${String(today.getDate()).padStart(2, "0")}`;
  console.log("Today:", todayStr);
  // Set end of today (23:59:59) as the cutoff for today's matches
  const tomorrow = new Date(today);
  tomorrow.setDate(today.getDate() + 1);
  tomorrow.setHours(0, 0, 0, 0); // Set to 00:00:00

  // Get matches for this week (next 7 days)
  const weekFromNow = new Date(today.getTime() + 7 * 24 * 60 * 60 * 1000);

  // Get later matches (beyond this week)
  const monthFromNow = new Date(today.getTime() + 30 * 24 * 60 * 60 * 1000);
  // Format date in local timezone as YYYY-MM-DD
  const monthStr = `${monthFromNow.getFullYear()}-${String(monthFromNow.getMonth() + 1).padStart(2, "0")}-${String(monthFromNow.getDate()).padStart(2, "0")}`;

  // Single API call to get all upcoming matches
  const {
    data: allMatches,
    isLoading: allMatchesLoading,
    error: allMatchesError,
  } = usePublicMatches({
    date_from: todayStr,
    date_to: monthStr,
    status: "scheduled",
    sort: "date",
    order: "asc",
    page_size: 200,
  });

  // Split matches into different time periods and extract competitions
  const {
    todayMatches,
    tomorrowMatches,
    weekMatches,
    laterMatches,
    availableCompetitions,
  } = React.useMemo(() => {
    if (!allMatches?.results) {
      return {
        todayMatches: [],
        tomorrowMatches: [],
        weekMatches: [],
        laterMatches: [],
        availableCompetitions: [],
      };
    }

    const matches = allMatches.results;
    const todayEnd = new Date(today);
    todayEnd.setHours(23, 59, 59, 999);

    const tomorrowEnd = new Date(tomorrow);
    tomorrowEnd.setHours(23, 59, 59, 999);

    const weekEnd = new Date(weekFromNow);
    weekEnd.setHours(23, 59, 59, 999);

    // Split matches by time period
    const todayMatchList: PublicMatch[] = [];
    const tomorrowMatchList: PublicMatch[] = [];
    const weekMatchList: PublicMatch[] = [];
    const laterMatchList: PublicMatch[] = [];

    matches.forEach((match) => {
      const matchDate = new Date(match.date || "");

      if (matchDate <= todayEnd) {
        todayMatchList.push(match);
      } else if (matchDate <= tomorrowEnd) {
        tomorrowMatchList.push(match);
      } else if (matchDate <= weekEnd) {
        weekMatchList.push(match);
      } else {
        laterMatchList.push(match);
      }
    });

    // Extract unique competitions
    const competitions = new Set<string>();
    matches.forEach((match) => {
      if (match.competition?.name) {
        competitions.add(match.competition.name);
      }
    });

    return {
      todayMatches: todayMatchList,
      tomorrowMatches: tomorrowMatchList,
      weekMatches: weekMatchList,
      laterMatches: laterMatchList,
      availableCompetitions: Array.from(competitions).sort(),
    };
  }, [allMatches, today, tomorrow, weekFromNow]);

  // tomorrowMatches is available for future use when adding tomorrow section

  // Helper function to filter matches by selected competitions and minimum star count
  const filterMatches = (matches: PublicMatch[]) => {
    return matches.filter((match) => {
      // Filter by competition
      const passesCompetitionFilter =
        selectedCompetitions.length === 0 ||
        (match.competition?.name &&
          selectedCompetitions.includes(match.competition.name));

      // Filter by minimum star count
      const matchStars = calculateMatchStars(
        match.team1?.elo || 1000,
        match.team2?.elo || 1000,
      );
      const passesStarFilter = matchStars >= minStarCount;

      return passesCompetitionFilter && passesStarFilter;
    });
  };

  // Helper function to sort matches by date then by stars (descending)
  const sortMatchesByDateAndStars = (matches: PublicMatch[]) => {
    return [...matches].sort((a, b) => {
      // First sort by date
      const dateA = new Date(a.date || 0).getTime();
      const dateB = new Date(b.date || 0).getTime();

      if (dateA !== dateB) {
        return dateA - dateB; // Earlier dates first
      }

      // If dates are the same, sort by stars (highest first)
      const starsA = calculateMatchStars(
        a.team1?.elo || 1000,
        a.team2?.elo || 1000,
      );
      const starsB = calculateMatchStars(
        b.team1?.elo || 1000,
        b.team2?.elo || 1000,
      );

      if (starsA !== starsB) {
        return starsB - starsA; // Higher stars first
      }

      // If stars are the same, sort by combined ELO (highest first)
      return (
        (b.team1.elo || 1000) +
        (b.team2.elo || 1000) -
        ((a.team1.elo || 1000) + (a.team2.elo || 1000))
      );
    });
  };

  if (allMatchesError) {
    return (
      <Alert variant="destructive" className="mt-4">
        <AlertTitle className="text-lg">Error</AlertTitle>
        <AlertDescription>
          There was an error loading upcoming matches. Please try again later.
        </AlertDescription>
      </Alert>
    );
  }

  return (
    <>
      {/* Competition Filter */}
      {(allMatchesLoading || availableCompetitions.length > 0) && (
        <div
          className={`competition-filter mb-4 w-full cursor-pointer rounded-xl border-2 p-4 ${
            isFilterExpanded ? "max-h-[1000px]" : "max-h-16"
          } transition-all duration-300`}
          onClick={() => setIsFilterExpanded(!isFilterExpanded)}
        >
          <div className="mb-2 flex items-center justify-between">
            <h2 className="font-semibold">Filter Matches</h2>
            <Menu />
          </div>
          <div
            className={`transition-all duration-200 ${
              isFilterExpanded ? "opacity-100" : "pointer-events-none opacity-0"
            }`}
          >
            {allMatchesLoading ? (
              <div className="flex h-10 items-center justify-center">
                <Spinner />
              </div>
            ) : (
              <>
                <div className="mt-4 grid grid-cols-1 gap-3 sm:grid-cols-2 md:grid-cols-3">
                  {availableCompetitions.map((competition) => (
                    <div
                      key={competition}
                      className="flex items-center space-x-2"
                      onClick={(e) => e.stopPropagation()}
                    >
                      <Checkbox
                        id={`competition-${competition}`}
                        checked={selectedCompetitions.includes(competition)}
                        onCheckedChange={(checked) => {
                          if (checked) {
                            setSelectedCompetitions([
                              ...selectedCompetitions,
                              competition,
                            ]);
                          } else {
                            setSelectedCompetitions(
                              selectedCompetitions.filter(
                                (c) => c !== competition,
                              ),
                            );
                          }
                        }}
                        onClick={(e) => e.stopPropagation()}
                      />
                      <Label
                        htmlFor={`competition-${competition}`}
                        className="text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70"
                        onClick={(e) => e.stopPropagation()}
                      >
                        {competition}
                      </Label>
                    </div>
                  ))}
                </div>
                <div className="mt-4 flex space-x-2">
                  <Button
                    onClick={(e) => {
                      e.stopPropagation();
                      setSelectedCompetitions(availableCompetitions);
                    }}
                    variant="outline"
                    size="sm"
                  >
                    Select All
                  </Button>
                  <Button
                    onClick={(e) => {
                      e.stopPropagation();
                      setSelectedCompetitions([]);
                    }}
                    variant="outline"
                    size="sm"
                  >
                    Clear All
                  </Button>
                </div>

                {/* Minimum Star Count Filter */}
                <div
                  className="mt-6 border-t pt-4"
                  onClick={(e) => e.stopPropagation()}
                >
                  <Label
                    htmlFor="min-star-count"
                    className="text-sm font-semibold"
                  >
                    Minimum Star Rating
                  </Label>
                  <div className="mt-2 flex items-center space-x-4">
                    <div className="flex items-center space-x-2">
                      {[0, 1, 2, 3, 4, 5].map((starCount) => (
                        <button
                          key={starCount}
                          onClick={(e) => {
                            e.stopPropagation();
                            setMinStarCount(starCount);
                          }}
                          className={`flex items-center space-x-1 rounded-md px-2 py-1 text-xs transition-colors ${
                            minStarCount === starCount
                              ? "bg-primary text-primary-foreground"
                              : "bg-muted text-muted-foreground hover:bg-muted/80"
                          }`}
                        >
                          <span>
                            {starCount === 0 ? "Any" : `${starCount}+`}
                          </span>
                          {starCount > 0 && (
                            <div className="flex">
                              {Array.from({ length: starCount }).map((_, i) => (
                                <Star
                                  key={i}
                                  size={10}
                                  className="fill-current"
                                />
                              ))}
                            </div>
                          )}
                        </button>
                      ))}
                    </div>
                  </div>
                </div>

                {/* Reset All Filters */}
                <div className="mt-4 flex justify-center border-t pt-4">
                  <Button
                    onClick={(e) => {
                      e.stopPropagation();
                      setSelectedCompetitions(availableCompetitions);
                      setMinStarCount(0);
                    }}
                    variant="outline"
                    size="sm"
                    className="text-muted-foreground"
                  >
                    Reset All Filters
                  </Button>
                </div>
              </>
            )}
          </div>
        </div>
      )}

      <h1>Today</h1>
      <hr />
      {allMatchesLoading ? (
        <div className="flex h-20 items-center justify-center">
          <Spinner />
        </div>
      ) : (
        (() => {
          const filteredTodayMatches = filterMatches(todayMatches);
          return filteredTodayMatches.length > 0 ? (
            <ul className="mt-3 grid grid-cols-1 gap-4 lg:grid-cols-2">
              {sortMatchesByDateAndStars(filteredTodayMatches).map((match) => (
                <UpcomingMatch
                  key={match.id}
                  match={match}
                  stars={calculateMatchStars(
                    match.team1?.elo || 1000,
                    match.team2?.elo || 1000,
                  )}
                />
              ))}
            </ul>
          ) : (
            <div className="text-muted-foreground my-4 text-center">
              No matches scheduled for today
            </div>
          );
        })()
      )}

      <h1 className="mt-8">Tomorrow</h1>
      <hr />
      {allMatchesLoading ? (
        <div className="flex h-20 items-center justify-center">
          <Spinner />
        </div>
      ) : (
        (() => {
          const filteredTomorrowMatches = filterMatches(tomorrowMatches);
          return filteredTomorrowMatches.length > 0 ? (
            <ul className="mt-3 grid grid-cols-1 gap-4 lg:grid-cols-2">
              {sortMatchesByDateAndStars(filteredTomorrowMatches).map(
                (match) => (
                  <UpcomingMatch
                    key={match.id}
                    match={match}
                    stars={calculateMatchStars(
                      match.team1?.elo || 1000,
                      match.team2?.elo || 1000,
                    )}
                  />
                ),
              )}
            </ul>
          ) : (
            <div className="text-muted-foreground my-4 text-center">
              No matches scheduled for tomorrow
            </div>
          );
        })()
      )}

      <h1 className="mt-8">This Week</h1>
      <hr />
      {allMatchesLoading ? (
        <div className="flex h-20 items-center justify-center">
          <Spinner />
        </div>
      ) : (
        (() => {
          const filteredWeekMatches = filterMatches(weekMatches);
          return filteredWeekMatches.length > 0 ? (
            <ul className="mt-3 grid grid-cols-1 gap-4 lg:grid-cols-2">
              {sortMatchesByDateAndStars(filteredWeekMatches).map((match) => (
                <UpcomingMatch
                  key={match.id}
                  match={match}
                  stars={calculateMatchStars(
                    match.team1?.elo || 1000,
                    match.team2?.elo || 1000,
                  )}
                />
              ))}
            </ul>
          ) : (
            <div className="text-muted-foreground my-4 text-center">
              No matches scheduled for this week
            </div>
          );
        })()
      )}

      <h1 className="mt-8">This Month</h1>
      <hr />
      {allMatchesLoading ? (
        <div className="flex h-20 items-center justify-center">
          <Spinner />
        </div>
      ) : (
        (() => {
          const filteredLaterMatches = filterMatches(laterMatches);
          return filteredLaterMatches.length > 0 ? (
            <ul className="mt-3 grid grid-cols-1 gap-4 lg:grid-cols-2">
              {sortMatchesByDateAndStars(filteredLaterMatches).map((match) => (
                <UpcomingMatch
                  key={match.id}
                  match={match}
                  stars={calculateMatchStars(
                    match.team1?.elo || 1000,
                    match.team2?.elo || 1000,
                  )}
                />
              ))}
            </ul>
          ) : (
            <div className="text-muted-foreground my-4 text-center">
              No matches scheduled for this month
            </div>
          );
        })()
      )}
    </>
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
  filters: MatchQueryParams;
  onFilterChange: (filters: Partial<MatchQueryParams>) => void;
}

function MatchesFilter({ filters, onFilterChange }: MatchesFilterProps) {
  const { data: seasonsData, isLoading } = usePublicSeasons();
  const seasons = seasonsData?.results || [];

  // Fetch competitions based on selected season
  const { data: competitionsData, isLoading: isLoadingCompetitions } =
    usePublicCompetitions({
      season_id: filters.season_id || undefined,
      page_size: 100,
    });
  const competitions = competitionsData?.results || [];

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
          disabled={isLoadingCompetitions}
        >
          <SelectTrigger id="competition">
            <SelectValue
              placeholder={
                isLoadingCompetitions ? "Loading..." : "Select a competition"
              }
            />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all_competitions">All Competitions</SelectItem>
            {competitions.map((competition) => (
              <SelectItem key={competition.id} value={competition.name}>
                {competition.name}
              </SelectItem>
            ))}
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
