import logo from "@/assets/0.1x/C Logo@0.1x.png";
import { ChevronRight, Star } from "lucide-react";

function UpcomingMatchesWidget() {
  return (
    <div className="matches-widget">
      <div className="group flex cursor-pointer items-center justify-between">
        <h2>Upcoming Matches</h2>
        <ChevronRight className="text-muted-foreground mr-2 h-6 w-6 transition-all group-hover:mr-0" />
      </div>
      <hr />
      <ul className="mt-2 space-y-2">
        <Match />
        <Match />
      </ul>
    </div>
  );
}

function Match() {
  return (
    <li className="flex rounded-xl border-2 p-4 py-2">
      <div className="flex-3 space-y-3">
        <div className="flex items-center space-x-2">
          <img src={logo} className="h-6 w-6" alt="Logo" />
          <span className="max-w-[120px] truncate overflow-ellipsis whitespace-nowrap">
            Syracuse University
          </span>
        </div>
        <div className="flex items-center space-x-2 overflow-ellipsis">
          <img src={logo} className="h-6 w-6" alt="Logo" />
          <span className="max-w-[120px] truncate overflow-ellipsis whitespace-nowrap">
            University of Texas
          </span>
        </div>
      </div>
      <div className="flex-1 text-end text-sm">
        <span className="text-muted-foreground">2025-10-01</span>
        <br />
        <span className="text-muted-foreground">3:00 PM</span>
        <br />

        <span className="text-muted-foreground space-x-.5 mt-1 flex items-center justify-end">
          <Star size={14} />
          <Star size={14} />
          <Star size={14} />
          <Star size={14} />
          <Star size={14} />
        </span>
      </div>
    </li>
  );
}

export default UpcomingMatchesWidget;
