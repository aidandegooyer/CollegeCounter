import player from "@/assets/player_silhouette.png";

function PlayerRankingComponent() {
  return (
    <div
      className={
        "team-ranking-component w-full cursor-pointer rounded-xl border-2 p-2 pl-4"
      }
    >
      <div className="flex justify-between">
        <div className="flex items-center space-x-2">
          <span className="mr-3 w-4 text-end font-mono text-xl">#</span>
          <img src={player} className="h-8 w-8 rounded-sm" alt="Logo" />
          <span className="truncate overflow-ellipsis whitespace-nowrap text-xl">
            Test Player
          </span>
        </div>
        <div>
          <div className="bg-secondary drop-shadow-secondary drop-shadow-lg/50 rounded-md p-1 px-2 font-mono text-lg">
            ####
          </div>
        </div>
      </div>
    </div>
  );
}

export default PlayerRankingComponent;
