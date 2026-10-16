import type { PublicMatch } from "@/services/api";

export type MatchResult = "win" | "loss" | "tie" | "unknown";

export const MATCH_RESULT_STYLES: Record<
  MatchResult,
  { label: string; badge: string; text: string }
> = {
  win: {
    label: "W",
    badge: "bg-green-500/15 text-green-500",
    text: "text-green-500",
  },
  loss: {
    label: "L",
    badge: "bg-red-500/15 text-red-500",
    text: "text-red-500",
  },
  tie: {
    label: "T",
    badge: "bg-muted text-muted-foreground",
    text: "text-muted-foreground",
  },
  unknown: {
    label: "?",
    badge: "bg-muted text-muted-foreground",
    text: "text-muted-foreground",
  },
};

// Result of a completed match from one team's perspective. With no winner set,
// equal scores are a tie; otherwise the result is unknown (likely missing data).
export function getMatchResult(
  match: Pick<PublicMatch, "winner" | "score_team1" | "score_team2">,
  teamId: string,
): MatchResult {
  if (match.winner) return match.winner.id === teamId ? "win" : "loss";
  return match.score_team1 === match.score_team2 ? "tie" : "unknown";
}

// Text color class matching the badge color, e.g. for scores
export function matchResultTextClass(result: MatchResult) {
  return MATCH_RESULT_STYLES[result].text;
}

export type TeamSummary = { id: string; name: string; picture?: string };

export type TeamRecord = { wins: number; losses: number; ties: number };

export function getOpponent(match: PublicMatch, teamId: string): TeamSummary {
  return match.team1.id === teamId ? match.team2 : match.team1;
}

export function getTeamInMatch(
  match: PublicMatch,
  teamId: string,
): TeamSummary {
  return match.team1.id === teamId ? match.team1 : match.team2;
}

// Team name taken from its match history, with a fallback when it has none
export function getTeamName(
  matches: PublicMatch[],
  teamId: string,
  fallback: string,
) {
  return matches[0] ? getTeamInMatch(matches[0], teamId).name : fallback;
}

// Score from the given team's perspective, e.g. "13 - 7"
export function getScore(match: PublicMatch, teamId: string) {
  return match.team1.id === teamId
    ? `${match.score_team1} - ${match.score_team2}`
    : `${match.score_team2} - ${match.score_team1}`;
}

export function formatMatchDate(date: string) {
  return new Date(date).toLocaleDateString(undefined, {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}

export function groupByOpponent(matches: PublicMatch[], teamId: string) {
  const groups = new Map<
    string,
    { opponent: TeamSummary; matches: PublicMatch[] }
  >();
  for (const match of matches) {
    const opponent = getOpponent(match, teamId);
    const group = groups.get(opponent.id);
    if (group) group.matches.push(match);
    else groups.set(opponent.id, { opponent, matches: [match] });
  }
  return groups;
}

// Matches with an "unknown" result are left out of the totals
export function getRecord(matches: PublicMatch[], teamId: string): TeamRecord {
  const results = matches.map((m) => getMatchResult(m, teamId));
  const count = (r: MatchResult) => results.filter((x) => x === r).length;
  return { wins: count("win"), losses: count("loss"), ties: count("tie") };
}
