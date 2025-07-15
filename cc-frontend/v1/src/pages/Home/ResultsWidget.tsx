import logo from "@/assets/0.1x/C Logo@0.1x.png";
import { ChevronRight } from "lucide-react";
import { NavLink } from "react-router";

function ResultsWidget() {
  return (
    <div className="matches-widget">
      <NavLink
        to="matches#past"
        className="group flex cursor-pointer items-center justify-between"
      >
        <h2>Past Matches</h2>
        <ChevronRight className="text-muted-foreground mr-2 h-6 w-6 transition-all group-hover:mr-0" />
      </NavLink>
      <hr />
      <ul className="mt-2 space-y-2">
        <Match />
        <Match />
        <Match />
        <Match />
      </ul>
    </div>
  );
}

function Match() {
  return (
    <li className="flex cursor-pointer rounded-xl border-2 p-4 py-2">
      <div className="flex-3 space-y-2">
        <div className="flex items-center space-x-2">
          <img src={logo} className="h-6 w-6" alt="Logo" />
          <span className="truncate overflow-ellipsis whitespace-nowrap font-semibold">
            Syracuse University
          </span>
        </div>
        <div className="flex items-center space-x-2 overflow-ellipsis">
          <img src={logo} className="h-6 w-6" alt="Logo" />
          <span className="text-muted-foreground truncate overflow-ellipsis whitespace-nowrap">
            University of Texas
          </span>
        </div>
      </div>
      <div className="flex-1 space-y-2 text-end">
        <span className="flex justify-end">
          <p className="bg-muted ml-2 rounded-sm px-1 font-mono text-green-500">
            2
          </p>
        </span>
        <span className="flex justify-end">
          <p className="bg-muted ml-2 rounded-sm px-1 font-mono text-red-500">
            1
          </p>
        </span>
      </div>
    </li>
  );
}

export default ResultsWidget;
