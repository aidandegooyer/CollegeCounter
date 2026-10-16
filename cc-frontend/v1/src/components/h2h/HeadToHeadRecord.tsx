import { MatchHistoryStatus } from "@/components/h2h/MatchHistoryStatus";
import { NavLink } from "react-router";
import Logo from "@/components/Logo";
import type { PublicMatch } from "@/services/api";
import { useMatchHistoryOrFetch } from "@/services/hooks";
import {
  formatMatchDate,
  getOpponent,
  getRecord,
  getTeamInMatch,
  getTeamName,
} from "@/services/matchResult";

// Record and list of matches two teams have played against each other.
// Pass `team1Matches` to reuse an existing fetch of team 1's history.
export function HeadToHeadRecord({
  team1Id,
  team2Id,
  team1Matches,
  team1Name: team1NameProp,
  team2Name: team2NameProp,
  title = "Head-to-Head",
}: {
  team1Id: string;
  team2Id: string;
  team1Matches?: PublicMatch[];
  /** Display names; derived from match history when omitted */
  team1Name?: string;
  team2Name?: string;
  title?: string;
}) {
  const history = useMatchHistoryOrFetch(team1Id, team1Matches);
  const matches = (history.matches ?? []).filter(
    (m) => getOpponent(m, team1Id).id === team2Id,
  );
  const record = getRecord(matches, team1Id);
  const team1Name =
    team1NameProp ?? getTeamName(history.matches ?? [], team1Id, "Team 1");
  const team2Name =
    team2NameProp ??
    (matches[0] ? getOpponent(matches[0], team1Id).name : "Team 2");

  return (
    <section>
      <h2 className="mb-4 text-2xl font-semibold">{title}</h2>
      <MatchHistoryStatus isLoading={history.isLoading} error={history.error} />
      {history.matches &&
        (matches.length === 0 ? (
          <div className="text-muted-foreground">
            These teams have not played each other.
          </div>
        ) : (
          <>
            <div className="mb-4 text-lg">
              {team1Name}{" "}
              <span className="font-bold">
                {record.wins} - {record.losses}
                {record.ties > 0 &&
                  ` (${record.ties} ${record.ties === 1 ? "tie" : "ties"})`}
              </span>{" "}
              {team2Name}
            </div>
            <ul className="divide-y rounded-lg border">
              {matches.map((match) => (
                <NeutralMatchRow
                  key={match.id}
                  match={match}
                  team1Id={team1Id}
                  team2Id={team2Id}
                />
              ))}
            </ul>
          </>
        ))}
    </section>
  );
}

// Shows both teams side by side with their scores, without a W/L/T badge.
// Team 1 is always on the left so rows line up.
function NeutralMatchRow({
  match,
  team1Id,
  team2Id,
}: {
  match: PublicMatch;
  team1Id: string;
  team2Id: string;
}) {
  const team1 = getTeamInMatch(match, team1Id);
  const team2 = getTeamInMatch(match, team2Id);
  const team1IsFirst = match.team1.id === team1Id;
  const team1Score = team1IsFirst ? match.score_team1 : match.score_team2;
  const team2Score = team1IsFirst ? match.score_team2 : match.score_team1;

  return (
    <li>
      <NavLink
        to={`/matches/${match.id}`}
        className="hover:bg-muted/50 grid grid-cols-[1fr_auto_1fr] items-center gap-3 px-3 py-2 text-sm"
      >
        <span className="flex min-w-0 items-center gap-2">
          <Logo
            type="team"
            src={team1.picture}
            className="h-6 w-6 shrink-0 rounded-sm object-cover"
          />
          <span className="truncate">{team1.name}</span>
        </span>
        <span className="flex flex-col items-center">
          <span className="font-semibold">
            {team1Score} - {team2Score}
          </span>
          <span className="text-muted-foreground text-xs">
            {formatMatchDate(match.date)}
          </span>
        </span>
        <span className="flex min-w-0 items-center justify-end gap-2">
          <span className="truncate text-right">{team2.name}</span>
          <Logo
            type="team"
            src={team2.picture}
            className="h-6 w-6 shrink-0 rounded-sm object-cover"
          />
        </span>
      </NavLink>
    </li>
  );
}
