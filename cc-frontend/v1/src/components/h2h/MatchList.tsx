import { NavLink } from "react-router";
import Logo from "@/components/Logo";
import { MatchResultBadge } from "@/components/MatchResultBadge";
import type { PublicMatch } from "@/services/api";
import {
  formatMatchDate,
  getMatchResult,
  getOpponent,
  getScore,
} from "@/services/matchResult";

// Compact list of matches from one team's perspective (result, opponent, score, date)
export function MatchList({
  matches,
  teamId,
  emptyMessage = "No completed matches.",
}: {
  matches: PublicMatch[];
  teamId: string;
  emptyMessage?: string;
}) {
  if (matches.length === 0) {
    return <div className="text-muted-foreground">{emptyMessage}</div>;
  }

  return (
    <ul className="divide-y rounded-lg border">
      {matches.map((match) => {
        const opponent = getOpponent(match, teamId);
        return (
          <li key={match.id}>
            <NavLink
              to={`/matches/${match.id}`}
              className="hover:bg-muted/50 flex items-center gap-3 px-3 py-2 text-sm"
            >
              <MatchResultBadge result={getMatchResult(match, teamId)} />
              <Logo
                type="team"
                src={opponent.picture}
                className="h-6 w-6 rounded-sm object-cover"
              />
              <span className="flex-1 truncate">vs {opponent.name}</span>
              <span className="font-semibold">{getScore(match, teamId)}</span>
              <span className="text-muted-foreground hidden w-24 text-right sm:inline">
                {formatMatchDate(match.date)}
              </span>
            </NavLink>
          </li>
        );
      })}
    </ul>
  );
}
