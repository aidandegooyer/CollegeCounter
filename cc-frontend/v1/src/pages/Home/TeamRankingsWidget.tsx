import logo from "@/assets/0.1x/C Logo@0.1x.png";
import { ChevronRight } from "lucide-react";

function TeamRankingsWidget() {
  return (
    <div className="rankings-widget rounded-xl border-2 px-4 py-2">
      <div className="group flex cursor-pointer items-center justify-between">
        <h2>Team Rankings</h2>
        <ChevronRight className="text-muted-foreground mr-2 h-6 w-6 transition-all group-hover:mr-0" />
      </div>
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
  return (
    <li className="flex justify-between">
      <div className="flex items-center space-x-2">
        <span className="mr-3 w-4 text-end font-mono">{rank}</span>
        <img src={logo} className="h-6 w-6 rounded-sm" alt="Logo" />
        <span>Test Team</span>
      </div>
      <div>
        <span className="bg-secondary rounded-md p-1 text-sm">#ELO</span>
      </div>
    </li>
  );
}

export default TeamRankingsWidget;
