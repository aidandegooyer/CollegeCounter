import logo from "@/assets/0.1x/C Logo@0.1x.png";
import { Radio } from "lucide-react";
import "./LiveMatchesWidget.css";
import { NavLink } from "react-router";

function LiveMatchesWidget() {
  return (
    <div className="matches-widget">
      <NavLink
        to="matches#live"
        className="flex cursor-pointer items-center justify-between"
      >
        <h2>Live Matches</h2>
        <Radio className="animate-radio-blink mr-2 h-6 w-6 text-red-500" />
      </NavLink>
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
      <div className="flex-3 space-y-2">
        <div className="flex items-center space-x-2">
          <img src={logo} className="h-6 w-6" alt="Logo" />
          <span className="truncate overflow-ellipsis whitespace-nowrap">
            Test University
          </span>
        </div>
        <div className="flex items-center space-x-2 overflow-ellipsis">
          <img src={logo} className="h-6 w-6" alt="Logo" />
          <span className="truncate overflow-ellipsis whitespace-nowrap">
            University of Test
          </span>
        </div>
      </div>
      <div className="flex-1 space-y-2 text-end">
        <span className="flex justify-end">
          <p className="font-mono text-green-500">11</p>
          <p className="bg-muted ml-2 rounded-sm px-1 font-mono text-red-500">
            0
          </p>
        </span>
        <span className="flex justify-end">
          <p className="font-mono text-red-500">4</p>
          <p className="bg-muted ml-2 rounded-sm px-1 font-mono text-green-500">
            1
          </p>
        </span>
      </div>
    </li>
  );
}

export default LiveMatchesWidget;
