import { CompetitionLabel } from "@/components/CompetitionLabel";
import { CountdownTimer } from "@/components/CountdownTimer";
import Logo from "@/components/Logo";
import type { PublicMatch } from "@/services/api";
import { calculateMatchStars } from "@/services/elo";
import { ExternalLink, Star } from "lucide-react";
import { NavLink } from "react-router";

const PLATFORM_NAMES: Record<string, string> = {
  faceit: "FACEIT",
  leaguespot: "LeagueSpot",
  regentsleague: "Regents League",
};

const locale = typeof navigator !== "undefined" ? navigator.language : "en-US";

interface MatchHeaderProps {
  match: PublicMatch;
  team1Rank?: number;
  team2Rank?: number;
}

export function MatchHeader({ match, team1Rank, team2Rank }: MatchHeaderProps) {
  const date = new Date(match.date);
  const hasScore =
    match.status === "completed" || match.status === "in_progress";
  // Only dim the trailing team once there is a score to compare
  const team1Behind = hasScore && match.score_team1 < match.score_team2;
  const team2Behind = hasScore && match.score_team2 < match.score_team1;
  const eloApplied = match.elo?.applied;

  return (
    <div className="mb-4 overflow-hidden rounded-2xl border-2">
      <div className="text-muted-foreground flex items-center justify-between gap-2 border-b px-4 py-2 text-sm">
        <div className="flex min-w-0 items-center gap-2">
          {match.competition && (
            <CompetitionLabel
              competition={match.competition.name}
              h={6}
              w={10}
            />
          )}
          <span className="truncate">
            {match.event_match?.event.name ?? match.season?.name}
          </span>
        </div>
        <StatusPill status={match.status} />
      </div>

      <div className="grid grid-cols-[1fr_auto_1fr] items-center gap-2 px-2 py-6 sm:gap-4 sm:px-6">
        <TeamColumn
          team={match.team1}
          rank={team1Rank}
          eloChange={eloApplied ? match.elo?.team1_change : null}
          dimmed={team1Behind}
        />

        <div className="flex flex-col items-center text-center">
          {hasScore ? (
            <div className="flex items-center gap-2 font-mono text-4xl font-bold sm:gap-3 sm:text-5xl">
              <span className={team1Behind ? "text-muted-foreground" : ""}>
                {match.score_team1}
              </span>
              <span className="text-muted-foreground text-2xl sm:text-3xl">
                :
              </span>
              <span className={team2Behind ? "text-muted-foreground" : ""}>
                {match.score_team2}
              </span>
            </div>
          ) : (
            <>
              <div className="text-2xl font-bold sm:text-3xl">
                {date.toLocaleTimeString(locale, {
                  hour: "numeric",
                  minute: "2-digit",
                })}
              </div>
              <div className="text-muted-foreground text-sm">
                {date.toLocaleDateString(locale, {
                  weekday: "short",
                  month: "short",
                  day: "numeric",
                })}
              </div>
            </>
          )}
        </div>

        <TeamColumn
          team={match.team2}
          rank={team2Rank}
          eloChange={eloApplied ? match.elo?.team2_change : null}
          dimmed={team2Behind}
        />
      </div>

      {match.status === "scheduled" && (
        <div className="-mt-2 pb-5">
          <CountdownTimer targetDate={date} size="sm" />
        </div>
      )}

      <div className="text-muted-foreground flex items-center justify-between gap-2 border-t px-4 py-2 text-sm">
        {match.status === "scheduled" ? (
          <MatchStars match={match} />
        ) : (
          <span>
            {date.toLocaleDateString(locale, {
              year: "numeric",
              month: "short",
              day: "numeric",
            })}
          </span>
        )}
        {match.url && (
          <a
            href={match.url.replace("{lang}", locale || "en")}
            target="_blank"
            rel="noopener noreferrer"
            className="hover:text-foreground flex items-center gap-1.5 font-medium"
          >
            View on{" "}
            {PLATFORM_NAMES[match.platform?.toLowerCase()] ?? "platform"}
            <ExternalLink className="h-3.5 w-3.5" />
          </a>
        )}
      </div>
    </div>
  );
}

function TeamColumn({
  team,
  rank,
  eloChange,
  dimmed,
}: {
  team: PublicMatch["team1"];
  rank?: number;
  eloChange?: number | null;
  dimmed: boolean;
}) {
  return (
    <NavLink
      to={`/teams/${team.id}`}
      className={`group flex min-w-0 flex-col items-center gap-2 text-center ${dimmed ? "opacity-60" : ""}`}
    >
      <Logo
        src={team.picture}
        className="h-16 w-16 rounded-md object-contain transition-transform group-hover:scale-105 sm:h-24 sm:w-24"
        alt={team.name}
        type="team"
      />
      <span className="flex w-full items-baseline justify-center gap-1.5">
        {rank != null && (
          <span className="text-muted-foreground shrink-0 text-xs sm:text-sm">
            #{rank}
          </span>
        )}
        <span className="truncate font-semibold group-hover:underline sm:text-xl">
          {team.name}
        </span>
      </span>
      {eloChange != null && eloChange !== 0 && (
        <span
          className={`font-mono text-xs sm:text-sm ${eloChange > 0 ? "text-green-500" : "text-red-500"}`}
        >
          {eloChange > 0 ? "+" : ""}
          {Math.round(eloChange)}
        </span>
      )}
    </NavLink>
  );
}

function StatusPill({ status }: { status: string }) {
  if (status === "in_progress") {
    return (
      <span className="flex shrink-0 items-center gap-1.5 rounded-full bg-red-500/15 px-2 py-0.5 text-xs font-semibold tracking-wide text-red-500 uppercase">
        <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-red-500" />
        Live
      </span>
    );
  }
  const label = status === "completed" ? "Final" : "Upcoming";
  return (
    <span className="bg-muted shrink-0 rounded-full px-2 py-0.5 text-xs font-semibold tracking-wide uppercase">
      {label}
    </span>
  );
}

function MatchStars({ match }: { match: PublicMatch }) {
  const stars = calculateMatchStars(
    match.team1.elo || 1000,
    match.team2.elo || 1000,
  );
  return (
    <span className="flex items-center gap-0.5" title={`${stars}/5 stars`}>
      {Array.from({ length: 5 }).map((_, i) => (
        <Star
          key={i}
          size={14}
          className={i < stars ? "fill-muted-foreground" : "opacity-30"}
        />
      ))}
    </span>
  );
}
