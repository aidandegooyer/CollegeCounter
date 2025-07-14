import player from "@/assets/player_silhouette.png";
import { ChevronRight } from "lucide-react";

function PlayerRankingsWidget() {
  return (
    <div className="rankings-widget rounded-xl border-2 px-4 py-2">
      <div className="group flex cursor-pointer items-center justify-between">
        <h2>Player Rankings</h2>
        <ChevronRight className="text-muted-foreground mr-2 h-6 w-6 transition-all group-hover:mr-0" />
      </div>
      <hr />
      <ul className="py-2 pt-3">
        {Array.from({ length: 10 }).map((_, i) => (
          <RankingItem key={i} index={i} />
        ))}
      </ul>
    </div>
  );
}

function RankingItem({ index }: { index: number }) {
  const rank = index + 1;

  return (
    <li
      className={
        "flex justify-between rounded-sm px-1 py-1.5" +
        (rank % 2 === 0 ? " bg-muted" : "")
      }
    >
      <div className="flex items-center space-x-2">
        <span className="w-4 text-end font-mono">{rank}</span>
        <img src={player} className="h-6 w-6 rounded-full" alt="Logo" />
        <span>Test Player</span>
      </div>
      <div>
        <span className="bg-primary rounded-md p-1 text-sm">#ELO</span>
      </div>
    </li>
  );
}

export default PlayerRankingsWidget;
