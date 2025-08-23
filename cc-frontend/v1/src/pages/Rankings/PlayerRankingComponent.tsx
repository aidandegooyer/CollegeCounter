import Logo from "@/components/Logo";
import type { PublicPlayer } from "@/services/api";

function PlayerRankingComponent(player: PublicPlayer & { rank: number }) {
  return (
    <div
      className={"team-ranking-component w-full rounded-xl border-2 p-2 pl-4"}
    >
      <div className="flex justify-between">
        <div className="flex items-center space-x-2">
          <span className="mr-3 text-end font-mono text-xl">
            {player.rank + 1}
          </span>
          <Logo
            src={player.picture}
            className="h-8 w-8 rounded-sm"
            alt="pfp"
            type="player"
          />
          <span className="truncate overflow-ellipsis whitespace-nowrap text-xl">
            {player.name}
          </span>
        </div>
        <div>
          <div className="bg-primary drop-shadow-primary drop-shadow-lg/50 rounded-md p-1 px-2 font-mono text-lg">
            {player.elo}
          </div>
        </div>
      </div>
    </div>
  );
}

export default PlayerRankingComponent;
