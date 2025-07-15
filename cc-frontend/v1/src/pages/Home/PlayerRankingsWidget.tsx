import player from "@/assets/player_silhouette.png";
import { ChevronRight } from "lucide-react";
import { NavLink } from "react-router";

function PlayerRankingsWidget() {
  return (
    <div className="rankings-widget rounded-xl border-2 px-4 py-2">
      <NavLink
        to="/rankings#player"
        className="group flex cursor-pointer items-center justify-between"
      >
        <h2>Player Rankings</h2>
        <ChevronRight className="text-muted-foreground mr-2 h-6 w-6 transition-all group-hover:mr-0" />
      </NavLink>
      <hr />
      <ul className="space-y-3 py-2 pt-3">
        {Array.from({ length: 10 }).map((_, i) => (
          <RankingItem key={i} index={i} />
        ))}
      </ul>
    </div>
  );
}

function RankingItem({ index }: { index: number }) {
  const rank = index + 1;
  const elo = Math.floor(Math.random() * (3000 - 1000 + 1)) + 1000;

  return (
    <li className="flex justify-between">
      <div className="flex items-center space-x-2">
        <span className="w-4 text-end font-mono">{rank}</span>
        <img src={player} className="h-6 w-6 rounded-full" alt="Logo" />
        <span className="truncate overflow-ellipsis whitespace-nowrap">
          Test Player
        </span>
      </div>
      <div>
        <span className="bg-primary drop-shadow-primary drop-shadow-lg/40 rounded-md p-1 font-mono text-sm">
          {elo}
        </span>
      </div>
    </li>
  );
}

export default PlayerRankingsWidget;
