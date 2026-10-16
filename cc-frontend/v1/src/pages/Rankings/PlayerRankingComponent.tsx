import Logo from "@/components/Logo";
import RankBadge from "@/components/RankBadge";
import type { PublicPlayer } from "@/services/api";

function PlayerRankingComponent(player: PublicPlayer & { rank: number }) {
  return (
    <div
      className={"team-ranking-component w-full rounded-xl border-2 p-2 pl-4"}
    >
      <div className="flex justify-between gap-2">
        <div className="flex min-w-0 items-center space-x-2">
          <span className="mr-3 text-end font-mono text-lg sm:text-xl">
            {player.rank + 1}
          </span>
          <div className="flex w-12 shrink-0 items-center justify-center sm:w-16">
            <Logo
              src={player.picture}
              className="h-12 rounded-sm sm:h-16"
              alt="pfp"
              type="player"
            />
          </div>
          <span className="min-w-0 truncate text-lg sm:text-xl">
            {player.name}
          </span>
          <div className="bg-secondary drop-shadow-secondary ml-2 hidden shrink-0 rounded-md p-1 px-2 text-xs drop-shadow-lg/50 sm:block">
            {player.team?.name}
          </div>
        </div>
        <div className="flex shrink-0 items-center space-x-2 sm:space-x-4">
          <RankBadge elo={player.elo || 0} className="h-8 w-8" />
          <div className="bg-primary drop-shadow-primary rounded-md p-1 px-2 font-mono text-lg drop-shadow-lg/50">
            {player.elo}
          </div>
        </div>
      </div>
    </div>
  );
}

export default PlayerRankingComponent;
