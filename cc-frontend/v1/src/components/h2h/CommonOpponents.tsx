import { useMemo, useState } from "react";
import { ChevronDown, ChevronRight } from "lucide-react";
import { NavLink } from "react-router";
import Logo from "@/components/Logo";
import { MatchHistoryStatus } from "@/components/h2h/MatchHistoryStatus";
import type { PublicMatch } from "@/services/api";
import { useMatchHistoryOrFetch } from "@/services/hooks";
import {
  type TeamSummary,
  formatMatchDate,
  getMatchResult,
  getRecord,
  getScore,
  getTeamName,
  groupByOpponent,
  matchResultTextClass,
} from "@/services/matchResult";

// Opponents both teams have played, with each team's record against them and
// an expandable list of those matches. Pass `team1Matches` / `team2Matches`
// to reuse existing fetches; otherwise each team's history is loaded here.
export function CommonOpponents({
  team1Id,
  team2Id,
  team1Matches,
  team2Matches,
  team1Name: team1NameProp,
  team2Name: team2NameProp,
  title = "Common Opponents",
}: {
  team1Id: string;
  team2Id: string;
  team1Matches?: PublicMatch[];
  team2Matches?: PublicMatch[];
  /** Display names; derived from match history when omitted */
  team1Name?: string;
  team2Name?: string;
  title?: string;
}) {
  const team1History = useMatchHistoryOrFetch(team1Id, team1Matches);
  const team2History = useMatchHistoryOrFetch(team2Id, team2Matches);

  const commonOpponents = useMemo(() => {
    if (!team1History.matches || !team2History.matches) return [];
    const team1ByOpponent = groupByOpponent(team1History.matches, team1Id);
    const team2ByOpponent = groupByOpponent(team2History.matches, team2Id);
    return [...team1ByOpponent.entries()]
      .filter(([id]) => id !== team2Id && team2ByOpponent.has(id))
      .map(([id, team1Games]) => ({
        opponent: team1Games.opponent,
        team1Matches: team1Games.matches,
        team2Matches: team2ByOpponent.get(id)!.matches,
      }))
      .sort((a, b) => a.opponent.name.localeCompare(b.opponent.name));
  }, [team1History.matches, team2History.matches, team1Id, team2Id]);

  const team1Name =
    team1NameProp ?? getTeamName(team1History.matches ?? [], team1Id, "Team 1");
  const team2Name =
    team2NameProp ?? getTeamName(team2History.matches ?? [], team2Id, "Team 2");
  const isLoading = team1History.isLoading || team2History.isLoading;
  const error = team1History.error ?? team2History.error;

  return (
    <section>
      <h2 className="mb-4 text-2xl font-semibold">{title}</h2>
      <MatchHistoryStatus isLoading={isLoading} error={error} />
      {!isLoading &&
        !error &&
        (commonOpponents.length === 0 ? (
          <div className="text-muted-foreground">
            These teams have no opponents in common.
          </div>
        ) : (
          <div className="overflow-x-auto rounded-lg border">
            <table className="w-full min-w-[640px] table-fixed text-sm">
              {/* Compact W/T/L columns; each team's match details span its three */}
              <colgroup>
                <col className="w-[34%]" />
                <col className="w-[11%]" />
                <col className="w-[11%]" />
                <col className="w-[11%]" />
                <col className="w-[11%]" />
                <col className="w-[11%]" />
                <col className="w-[11%]" />
              </colgroup>
              <thead className="bg-muted/50">
                <tr>
                  <th rowSpan={2} className="px-3 py-2 text-left">
                    Opponent
                  </th>
                  <th colSpan={3} className="border-l px-3 pt-2 text-center">
                    {team1Name}
                  </th>
                  <th colSpan={3} className="border-l px-3 pt-2 text-center">
                    {team2Name}
                  </th>
                </tr>
                <tr className="text-muted-foreground text-xs">
                  <th className="border-l px-3 pb-2 text-center">Wins</th>
                  <th className="px-3 pb-2 text-center">Ties</th>
                  <th className="px-3 pb-2 text-center">Losses</th>
                  <th className="border-l px-3 pb-2 text-center">Wins</th>
                  <th className="px-3 pb-2 text-center">Ties</th>
                  <th className="px-3 pb-2 text-center">Losses</th>
                </tr>
              </thead>
              <tbody>
                {commonOpponents.map((row) => (
                  <CommonOpponentRow
                    key={row.opponent.id}
                    {...row}
                    team1Id={team1Id}
                    team2Id={team2Id}
                  />
                ))}
              </tbody>
            </table>
          </div>
        ))}
    </section>
  );
}

function CommonOpponentRow({
  opponent,
  team1Id,
  team2Id,
  team1Matches,
  team2Matches,
}: {
  opponent: TeamSummary;
  team1Id: string;
  team2Id: string;
  team1Matches: PublicMatch[];
  team2Matches: PublicMatch[];
}) {
  const [isOpen, setIsOpen] = useState(false);
  const team1Record = getRecord(team1Matches, team1Id);
  const team2Record = getRecord(team2Matches, team2Id);

  return (
    <>
      <tr
        className="hover:bg-muted/30 cursor-pointer border-t"
        onClick={() => setIsOpen((open) => !open)}
      >
        <td className="px-3 py-2">
          <div className="flex items-center gap-2">
            <NavLink
              to={`/teams/${opponent.id}`}
              onClick={(e) => e.stopPropagation()}
              className="flex min-w-0 items-center gap-2 hover:underline"
            >
              <Logo
                type="team"
                src={opponent.picture}
                className="h-6 w-6 shrink-0 rounded-sm object-cover"
              />
              <span className="truncate" title={opponent.name}>
                {opponent.name}
              </span>
            </NavLink>
            <ChevronDown
              aria-label={isOpen ? "Hide matches" : "Show matches"}
              className={`size-4 shrink-0 transition-transform ${isOpen ? "rotate-180" : ""}`}
            />
          </div>
        </td>
        <td className="border-l px-3 py-2 text-center">{team1Record.wins}</td>
        <td className="px-3 py-2 text-center">{team1Record.ties}</td>
        <td className="px-3 py-2 text-center">{team1Record.losses}</td>
        <td className="border-l px-3 py-2 text-center">{team2Record.wins}</td>
        <td className="px-3 py-2 text-center">{team2Record.ties}</td>
        <td className="px-3 py-2 text-center">{team2Record.losses}</td>
      </tr>
      {isOpen && (
        <tr className="bg-muted/20">
          <td />
          <td colSpan={3} className="border-l px-3 py-2 align-top">
            <OpponentMatchDetails matches={team1Matches} teamId={team1Id} />
          </td>
          <td colSpan={3} className="border-l px-3 py-2 align-top">
            <OpponentMatchDetails matches={team2Matches} teamId={team2Id} />
          </td>
        </tr>
      )}
    </>
  );
}

function OpponentMatchDetails({
  matches,
  teamId,
}: {
  matches: PublicMatch[];
  teamId: string;
}) {
  return (
    <div>
      <table className="w-full text-xs">
        <thead className="text-muted-foreground">
          <tr>
            <th className="py-1 text-left font-medium">Date</th>
            <th className="py-1 text-left font-medium">Competition</th>
            <th className="py-1 text-center font-medium">Score</th>
            <th className="w-6" />
          </tr>
        </thead>
        <tbody>
          {matches.map((match) => (
            <tr key={match.id} className="border-t">
              <td className="py-1">
                <NavLink
                  to={`/matches/${match.id}`}
                  className="hover:underline"
                >
                  {formatMatchDate(match.date)}
                </NavLink>
              </td>
              <td className="py-1">
                {match.competition?.name ??
                  match.event_match?.event.name ??
                  "—"}
              </td>
              <td
                className={`py-1 text-center font-semibold ${matchResultTextClass(
                  getMatchResult(match, teamId),
                )}`}
              >
                {getScore(match, teamId)}
              </td>
              <td className="py-1 text-right">
                <NavLink
                  to={`/matches/${match.id}`}
                  aria-label="View match"
                  className="text-muted-foreground hover:text-foreground inline-flex"
                >
                  <ChevronRight className="size-4" />
                </NavLink>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
