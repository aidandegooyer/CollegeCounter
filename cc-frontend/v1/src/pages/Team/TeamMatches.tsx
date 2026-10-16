import Logo from "@/components/Logo";
import { Alert, AlertTitle, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Spinner } from "@/components/ui/shadcn-io/spinner";
import type { PublicMatch } from "@/services/api";
import { calculateMatchStars } from "@/services/elo";
import { useInfinitePublicMatches, usePublicMatches } from "@/services/hooks";
import { Star } from "lucide-react";
import { useMemo } from "react";
import { Link, useLocation, useNavigate } from "react-router";

const PAGE_SIZE = 10;

type Tab = "upcoming" | "results";

interface TeamMatchesProps {
  teamId: string;
}

// A team's matches seen from its own side: the opponent, the result, and the
// team's score first
export default function TeamMatches({ teamId }: TeamMatchesProps) {
  // The selected tab lives in the hash, so back/forward switch tabs
  const location = useLocation();
  const navigate = useNavigate();
  const tab: Tab = location.hash === "#results" ? "results" : "upcoming";
  const setTab = (t: Tab) => {
    if (t !== tab) navigate({ hash: t }, { replace: true });
  };

  return (
    <section className="mx-4 mt-8">
      <div className="mb-3 flex items-center justify-between gap-4">
        <h2 className="text-2xl">Matches</h2>
        <div className="bg-card flex rounded-lg border p-1 text-sm">
          {(["upcoming", "results"] as const).map((t) => (
            <button
              key={t}
              type="button"
              onClick={() => setTab(t)}
              className={`rounded-md px-3 py-1 capitalize transition-colors ${
                tab === t
                  ? "bg-muted font-semibold"
                  : "text-muted-foreground hover:text-foreground cursor-pointer"
              }`}
            >
              {t}
            </button>
          ))}
        </div>
      </div>

      <LiveMatches teamId={teamId} />
      {tab === "upcoming" ? (
        <MatchList teamId={teamId} kind="upcoming" />
      ) : (
        <MatchList teamId={teamId} kind="results" />
      )}
    </section>
  );
}

function LiveMatches({ teamId }: TeamMatchesProps) {
  const { data } = usePublicMatches(
    { team_id: teamId, status: "in_progress", sort: "date", order: "asc" },
    { refetchInterval: 1000 * 60 },
  );
  const matches = data?.results ?? [];
  if (matches.length === 0) return null;

  return (
    <ul className="mb-3 space-y-2">
      {matches.map((match) => (
        <MatchRow key={match.id} match={match} teamId={teamId} live />
      ))}
    </ul>
  );
}

function MatchList({
  teamId,
  kind,
}: TeamMatchesProps & { kind: "upcoming" | "results" }) {
  // Start of today keeps the query key stable for the whole day
  const today = useMemo(() => {
    const d = new Date();
    d.setHours(0, 0, 0, 0);
    return d.toISOString().split("T")[0];
  }, []);

  const {
    data,
    isLoading,
    error,
    fetchNextPage,
    hasNextPage,
    isFetchingNextPage,
  } = useInfinitePublicMatches(
    kind === "upcoming"
      ? {
          team_id: teamId,
          status: "scheduled",
          date_from: today,
          sort: "date",
          order: "asc",
          page_size: PAGE_SIZE,
        }
      : {
          team_id: teamId,
          status: "completed",
          sort: "date",
          order: "desc",
          page_size: PAGE_SIZE,
        },
  );

  if (isLoading) {
    return (
      <div className="flex h-40 items-center justify-center">
        <Spinner />
      </div>
    );
  }
  if (error || !data) {
    return (
      <Alert variant="destructive">
        <AlertTitle>Error</AlertTitle>
        <AlertDescription>
          There was an error loading matches. Please try again later.
        </AlertDescription>
      </Alert>
    );
  }

  const matches = data.pages.flatMap((page) => page.results);
  if (matches.length === 0) {
    return (
      <div className="text-muted-foreground rounded-xl border-2 border-dashed py-10 text-center">
        {kind === "upcoming" ? "No upcoming matches" : "No results yet"}
      </div>
    );
  }

  return (
    <>
      {kind === "results" && <Form matches={matches} teamId={teamId} />}
      <ul className="divide-y overflow-hidden rounded-xl border-2">
        {matches.map((match) => (
          <MatchRow key={match.id} match={match} teamId={teamId} />
        ))}
      </ul>
      {hasNextPage && (
        <div className="mt-3 flex justify-center">
          <Button
            variant="outline"
            onClick={() => fetchNextPage()}
            disabled={isFetchingNextPage}
          >
            {isFetchingNextPage ? <Spinner className="h-4 w-4" /> : "Show more"}
          </Button>
        </div>
      )}
    </>
  );
}

// The team's side of a match, whichever slot it was in
function perspective(match: PublicMatch, teamId: string) {
  const isTeam1 = match.team1.id === teamId;
  return {
    opponent: isTeam1 ? match.team2 : match.team1,
    ourScore: isTeam1 ? match.score_team1 : match.score_team2,
    theirScore: isTeam1 ? match.score_team2 : match.score_team1,
    eloChange: isTeam1 ? match.elo?.team1_change : match.elo?.team2_change,
    outcome: !match.winner ? "D" : match.winner.id === teamId ? "W" : "L",
  } as const;
}

const OUTCOME_STYLES = {
  W: "bg-green-500/15 text-green-500",
  L: "bg-red-500/15 text-red-500",
  D: "bg-muted text-muted-foreground",
};

function Form({ matches, teamId }: { matches: PublicMatch[]; teamId: string }) {
  const recent = matches.slice(0, 5);
  return (
    <div className="text-muted-foreground mb-3 flex items-center gap-2 text-sm">
      <span>Last {recent.length}</span>
      {/* Oldest to newest so the streak reads left to right */}
      {[...recent].reverse().map((match) => {
        const { outcome } = perspective(match, teamId);
        return (
          <span
            key={match.id}
            className={`flex h-6 w-6 items-center justify-center rounded font-mono text-xs font-bold ${OUTCOME_STYLES[outcome]}`}
          >
            {outcome}
          </span>
        );
      })}
    </div>
  );
}

function MatchRow({
  match,
  teamId,
  live = false,
}: {
  match: PublicMatch;
  teamId: string;
  live?: boolean;
}) {
  const { opponent, ourScore, theirScore, eloChange, outcome } = perspective(
    match,
    teamId,
  );
  const completed = match.status === "completed";
  const date = new Date(match.date);

  return (
    <li className={live ? "rounded-xl border-2 border-red-500/50" : undefined}>
      <Link
        to={`/matches/${match.id}`}
        className="hover:bg-muted/50 flex items-center gap-3 px-4 py-3 transition-colors"
      >
        <div className="text-muted-foreground w-14 shrink-0 text-xs leading-tight">
          {live ? (
            <span className="flex items-center gap-1.5 font-semibold text-red-500">
              <span className="h-2 w-2 animate-pulse rounded-full bg-red-500" />
              LIVE
            </span>
          ) : (
            <>
              <div className="text-foreground font-medium">
                {date.toLocaleDateString(undefined, {
                  month: "short",
                  day: "numeric",
                })}
              </div>
              <div>
                {completed
                  ? date.getFullYear()
                  : date.toLocaleTimeString(undefined, {
                      hour: "numeric",
                      minute: "2-digit",
                    })}
              </div>
            </>
          )}
        </div>

        <div className="flex min-w-0 flex-1 items-center gap-2">
          <span className="text-muted-foreground text-xs">vs</span>
          <Logo
            src={opponent.picture}
            className="h-7 w-7 shrink-0 rounded-sm"
            alt={opponent.name}
            type="team"
          />
          <div className="min-w-0">
            <div className="truncate font-medium">{opponent.name}</div>
            {match.competition?.name && (
              <div className="text-muted-foreground truncate text-xs">
                {match.competition.name}
              </div>
            )}
          </div>
        </div>

        {completed ? (
          <div className="flex shrink-0 items-center gap-3">
            {eloChange != null && (
              <span
                className={`hidden font-mono text-xs sm:inline ${
                  eloChange >= 0 ? "text-green-500" : "text-red-500"
                }`}
                title="Elo change"
              >
                {eloChange >= 0 ? "+" : ""}
                {eloChange}
              </span>
            )}
            <span className="font-mono tabular-nums">
              {ourScore}
              <span className="text-muted-foreground mx-1">–</span>
              {theirScore}
            </span>
            <span
              className={`flex h-6 w-6 items-center justify-center rounded font-mono text-xs font-bold ${OUTCOME_STYLES[outcome]}`}
            >
              {outcome}
            </span>
          </div>
        ) : live ? (
          <span className="shrink-0 font-mono tabular-nums">
            {ourScore}
            <span className="text-muted-foreground mx-1">–</span>
            {theirScore}
          </span>
        ) : (
          <Stars
            count={calculateMatchStars(
              match.team1.elo || 1000,
              match.team2.elo || 1000,
            )}
          />
        )}
      </Link>
    </li>
  );
}

function Stars({ count }: { count: number }) {
  return (
    <span
      className="flex shrink-0 items-center gap-0.5"
      title={`${count} star match`}
    >
      {Array.from({ length: 5 }).map((_, i) => (
        <Star
          key={i}
          size={12}
          className={
            i < count
              ? "fill-muted-foreground text-muted-foreground"
              : "text-muted"
          }
        />
      ))}
    </span>
  );
}
