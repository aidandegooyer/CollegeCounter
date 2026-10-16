import Logo from "@/components/Logo";
import RankBadge from "@/components/RankBadge";
import { Alert, AlertTitle, AlertDescription } from "@/components/ui/alert";
import { Spinner } from "@/components/ui/shadcn-io/spinner";
import type { PublicPlayer } from "@/services/api";
import { usePublicPlayers } from "@/services/hooks";
import { ExternalLink } from "lucide-react";

interface TeamRosterProps {
  teamId: string;
}

export default function TeamRoster({ teamId }: TeamRosterProps) {
  const { data, isLoading, error } = usePublicPlayers({
    team_id: teamId,
    visible: true,
    sort: "elo",
    order: "desc",
    page_size: 50,
  });

  // Only list players who have a Steam account linked
  const players = data?.results.filter((p) => p.steam_id) ?? [];

  function renderBody() {
    if (isLoading) {
      return (
        <div className="flex h-32 items-center justify-center">
          <Spinner />
        </div>
      );
    }
    if (error || !data) {
      return (
        <Alert variant="destructive">
          <AlertTitle>Error</AlertTitle>
          <AlertDescription>
            There was an error loading the roster. Please try again later.
          </AlertDescription>
        </Alert>
      );
    }
    if (players.length === 0) {
      return (
        <div className="text-muted-foreground rounded-xl border-2 border-dashed py-10 text-center">
          No players listed for this team
        </div>
      );
    }

    const active = players.filter((p) => !p.benched);
    const bench = players.filter((p) => p.benched);
    return (
      <>
        <PlayerGrid players={active} />
        {bench.length > 0 && (
          <>
            <h3 className="text-muted-foreground mt-4 mb-2 text-sm font-semibold tracking-wide uppercase">
              Bench
            </h3>
            <PlayerGrid players={bench} muted />
          </>
        )}
      </>
    );
  }

  return (
    <section className="mx-4">
      <h2 className="mb-3 text-2xl">Roster</h2>
      {renderBody()}
    </section>
  );
}

function PlayerGrid({
  players,
  muted = false,
}: {
  players: PublicPlayer[];
  muted?: boolean;
}) {
  return (
    <ul
      className={`grid grid-cols-1 gap-2 sm:grid-cols-2 md:grid-cols-3 ${muted ? "opacity-70" : ""}`}
    >
      {players.map((player) => (
        <PlayerCard key={player.id} player={player} />
      ))}
    </ul>
  );
}

function PlayerCard({ player }: { player: PublicPlayer }) {
  return (
    <li className="flex items-center gap-3 rounded-xl border-2 p-3">
      <Logo
        src={player.picture}
        className="h-14 w-14 shrink-0 rounded-md object-cover"
        alt={player.name}
        type="player"
      />
      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-1.5">
          <span className="truncate font-semibold">{player.name}</span>
          {player.steam_id && (
            <a
              href={`https://steamcommunity.com/profiles/${player.steam_id}`}
              target="_blank"
              rel="noopener noreferrer"
              className="text-muted-foreground hover:text-foreground shrink-0"
              title="Steam profile"
              aria-label={`${player.name} on Steam`}
            >
              <ExternalLink className="h-3.5 w-3.5" />
            </a>
          )}
        </div>
        <div className="text-muted-foreground mt-1 flex items-center gap-1.5 text-sm">
          {player.elo ? (
            <>
              <RankBadge elo={player.elo} className="h-6 w-6" />
              <span className="font-mono">{player.elo}</span>
            </>
          ) : (
            "Unranked"
          )}
        </div>
      </div>
    </li>
  );
}
