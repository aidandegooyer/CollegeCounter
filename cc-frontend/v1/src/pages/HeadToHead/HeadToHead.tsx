import { useEffect, useState } from "react";
import { NavLink, useSearchParams } from "react-router";
import { CommonOpponents } from "@/components/h2h/CommonOpponents";
import { HeadToHeadRecord } from "@/components/h2h/HeadToHeadRecord";
import Logo from "@/components/Logo";
import { RecentMatches } from "@/components/h2h/RecentMatches";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Spinner } from "@/components/ui/shadcn-io/spinner";
import {
  usePublicTeams,
  useTeamDetails,
  useTeamMatchHistory,
} from "@/services/hooks";

const RECENT_MATCH_COUNT = 10;

export function HeadToHead() {
  const [searchParams, setSearchParams] = useSearchParams();
  const team1Id = searchParams.get("team1") ?? undefined;
  const team2Id = searchParams.get("team2") ?? undefined;

  // Keep the selection in the URL so a comparison can be shared
  const setTeam = (key: "team1" | "team2", id: string | undefined) => {
    const next = new URLSearchParams(searchParams);
    if (id) next.set(key, id);
    else next.delete(key);
    setSearchParams(next, { replace: true });
  };

  const team1History = useTeamMatchHistory(team1Id);
  const team2History = useTeamMatchHistory(team2Id);

  // Same query keys as the pickers, so these don't refetch
  const team1Details = useTeamDetails(team1Id);
  const team2Details = useTeamDetails(team2Id);
  const team1Name = team1Details.data?.name ?? "Team 1";
  const team2Name = team2Details.data?.name ?? "Team 2";

  const bothSelected = Boolean(team1Id && team2Id);
  const failedTeams = [
    team1History.isError && team1Name,
    team2History.isError && team2Name,
  ].filter(Boolean);
  const hasError = failedTeams.length > 0;
  const isLoading =
    !hasError && (team1History.isLoading || team2History.isLoading);
  const retry = () => {
    if (team1History.isError) team1History.refetch();
    if (team2History.isError) team2History.refetch();
  };

  return (
    <div className="container mx-auto max-w-[1200px] px-4 py-8">
      <h1 className="mb-6 text-3xl font-bold">Head to Head</h1>

      <div className="grid gap-4 md:grid-cols-2">
        <TeamPicker
          label="Team 1"
          teamId={team1Id}
          excludeId={team2Id}
          onChange={(id) => setTeam("team1", id)}
        />
        <TeamPicker
          label="Team 2"
          teamId={team2Id}
          excludeId={team1Id}
          onChange={(id) => setTeam("team2", id)}
        />
      </div>

      {!bothSelected && (
        <div className="text-muted-foreground mt-10 text-center">
          Select two teams to compare.
        </div>
      )}

      {bothSelected && isLoading && (
        <div className="mt-10 flex flex-col items-center">
          <Spinner />
          <div className="text-muted-foreground mt-2 text-sm">
            Loading match history...
          </div>
        </div>
      )}

      {bothSelected && hasError && (
        <div className="mt-10 flex flex-col items-center gap-3">
          <div className="text-destructive text-center">
            Failed to load match history for {failedTeams.join(" and ")}.
          </div>
          <Button variant="outline" onClick={retry}>
            Retry
          </Button>
        </div>
      )}

      {bothSelected &&
        !hasError &&
        team1History.data &&
        team2History.data &&
        team1Id &&
        team2Id && (
          <div className="mt-8 space-y-10">
            <HeadToHeadRecord
              team1Id={team1Id}
              team2Id={team2Id}
              team1Matches={team1History.data.results}
              team1Name={team1Name}
              team2Name={team2Name}
            />

            <section>
              <h2 className="mb-4 text-2xl font-semibold">
                Last {RECENT_MATCH_COUNT} Matches
              </h2>
              <div className="grid gap-6 md:grid-cols-2">
                <RecentMatches
                  teamId={team1Id}
                  matches={team1History.data.results}
                  limit={RECENT_MATCH_COUNT}
                  title={team1Name}
                />
                <RecentMatches
                  teamId={team2Id}
                  matches={team2History.data.results}
                  limit={RECENT_MATCH_COUNT}
                  title={team2Name}
                />
              </div>
            </section>

            <CommonOpponents
              team1Id={team1Id}
              team2Id={team2Id}
              team1Matches={team1History.data.results}
              team2Matches={team2History.data.results}
              team1Name={team1Name}
              team2Name={team2Name}
            />
          </div>
        )}
    </div>
  );
}

function TeamPicker({
  label,
  teamId,
  excludeId,
  onChange,
}: {
  label: string;
  teamId: string | undefined;
  excludeId: string | undefined;
  onChange: (id: string | undefined) => void;
}) {
  const [query, setQuery] = useState("");
  const [debouncedQuery, setDebouncedQuery] = useState("");

  useEffect(() => {
    const timeout = setTimeout(() => setDebouncedQuery(query.trim()), 300);
    return () => clearTimeout(timeout);
  }, [query]);

  const selected = useTeamDetails(teamId);
  const selectedTeam = selected.data;
  const search = usePublicTeams(
    { name: debouncedQuery, page_size: 10 },
    { enabled: !teamId && debouncedQuery.length > 0 },
  );
  const searchResults = search.data;
  const isFetching = search.isFetching;

  // useTeamDetails resolves to null when the id matches no team
  const selectedName = selected.isError
    ? "Failed to load team"
    : selected.isLoading
      ? "Loading..."
      : (selectedTeam?.name ?? "Team not found");

  const options = (searchResults?.results ?? []).filter(
    (team) => team.id !== excludeId,
  );

  return (
    <div className="bg-card rounded-lg border p-4">
      <div className="text-muted-foreground mb-2 text-sm font-semibold">
        {label}
      </div>

      {teamId ? (
        <div className="flex items-center justify-between gap-4">
          <NavLink
            to={`/teams/${teamId}`}
            className="flex items-center gap-3 hover:underline"
          >
            <Logo
              type="team"
              src={selectedTeam?.picture}
              className="h-12 w-12 rounded-sm object-cover"
            />
            <span className="text-lg font-semibold">{selectedName}</span>
          </NavLink>
          <Button
            variant="outline"
            onClick={() => {
              setQuery("");
              onChange(undefined);
            }}
          >
            Change
          </Button>
        </div>
      ) : (
        <div className="relative">
          <Input
            placeholder="Search for a team..."
            value={query}
            onChange={(e) => setQuery(e.target.value)}
          />
          {debouncedQuery && (
            <ul className="bg-popover absolute z-10 mt-1 max-h-72 w-full overflow-y-auto rounded-md border shadow-md">
              {isFetching && (
                <li className="text-muted-foreground px-3 py-2 text-sm">
                  Searching...
                </li>
              )}
              {!isFetching && search.isError && (
                <li className="text-destructive flex items-center justify-between px-3 py-2 text-sm">
                  Couldn't search teams.
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => search.refetch()}
                  >
                    Retry
                  </Button>
                </li>
              )}
              {!isFetching && !search.isError && options.length === 0 && (
                <li className="text-muted-foreground px-3 py-2 text-sm">
                  No teams found
                </li>
              )}
              {!isFetching &&
                options.map((team) => (
                  <li key={team.id}>
                    <button
                      type="button"
                      className="hover:bg-muted flex w-full cursor-pointer items-center gap-3 px-3 py-2 text-left"
                      onClick={() => onChange(team.id)}
                    >
                      <Logo
                        type="team"
                        src={team.picture}
                        className="h-8 w-8 rounded-sm object-cover"
                      />
                      <span>{team.name}</span>
                    </button>
                  </li>
                ))}
            </ul>
          )}
        </div>
      )}
    </div>
  );
}
