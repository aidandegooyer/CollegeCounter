import logo from "@/assets/0.1x/C Logo@0.1x.png";
import player from "@/assets/player_silhouette.png";
import { useState } from "react";

function TeamRankingComponent() {
  const [expanded, setExpanded] = useState(false);
  return (
    <div
      className={
        "team-ranking-component w-full cursor-pointer rounded-xl border-2 p-2 pl-4"
      }
      onClick={() => setExpanded(!expanded)}
    >
      <div className="flex justify-between">
        <div className="flex items-center space-x-2">
          <span className="mr-3 w-4 text-end font-mono text-xl">#</span>
          <img src={logo} className="h-8 w-8 rounded-sm" alt="Logo" />
          <span className="truncate overflow-ellipsis whitespace-nowrap text-xl">
            Test Team
          </span>
        </div>
        <div>
          <div className="bg-secondary drop-shadow-secondary drop-shadow-lg/50 rounded-md p-1 px-2 font-mono text-lg">
            ####
          </div>
        </div>
      </div>
      <div
        className={`hidden transition-all duration-300 md:block ${expanded ? "max-h-[500px]" : "max-h-0 overflow-hidden"}`}
      >
        <div className="mx-12 flex justify-between">
          {Array.from({ length: 5 }).map((_, i) => (
            <div key={i}>
              <img src={player} className="h-32 w-32" alt="Player" />
              <p className="border-t-2 text-center">Player {i + 1}</p>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

export default TeamRankingComponent;
