import { MatchHistoryStatus } from "@/components/h2h/MatchHistoryStatus";
import { MatchList } from "@/components/h2h/MatchList";
import type { PublicMatch } from "@/services/api";
import { useMatchHistoryOrFetch } from "@/services/hooks";

// A team's most recent completed matches. Pass `matches` to reuse an existing
// fetch; otherwise the team's history is loaded here.
export function RecentMatches({
  teamId,
  matches,
  limit = 10,
  title,
}: {
  teamId: string;
  matches?: PublicMatch[];
  limit?: number;
  title?: string;
}) {
  const history = useMatchHistoryOrFetch(teamId, matches);

  return (
    <div>
      {title && <h3 className="mb-2 font-semibold">{title}</h3>}
      <MatchHistoryStatus isLoading={history.isLoading} error={history.error} />
      {history.matches && (
        <MatchList matches={history.matches.slice(0, limit)} teamId={teamId} />
      )}
    </div>
  );
}
