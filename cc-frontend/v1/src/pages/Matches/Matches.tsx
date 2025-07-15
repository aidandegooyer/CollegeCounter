import { ArrowRight, Star } from "lucide-react";
import logo from "@/assets/0.1x/C Logo@0.1x.png";
import { useState } from "react";
import { Button } from "@/components/ui/button";

function Matches() {
  var initMatchType = "upcoming";
  const hash = window.location.hash.replace("#", "");
  if (hash === "live" || hash === "past") {
    initMatchType = hash;
  }

  const [matchType, setMatchType] = useState(initMatchType || "live");

  return (
    <div className="app-container mx-4 flex justify-center">
      <div className="matches w-full max-w-[1000px]">
        <div className="flex justify-center">
          <div className="my-4 flex h-12 w-[500px] rounded-xl border-2">
            <div
              onClick={() => setMatchType("live")}
              className={`flex-2 group flex items-center justify-center rounded-lg ${matchType === "live" ? "bg-muted" : "cursor-pointer"}`}
            >
              <h2
                className={`transition-colors duration-200 ${
                  matchType === "live"
                    ? ""
                    : "text-muted-foreground group-hover:text-foreground"
                }`}
              >
                Live
              </h2>
            </div>
            <div
              onClick={() => setMatchType("upcoming")}
              className={`flex-3 group flex items-center justify-center rounded-lg ${matchType === "upcoming" ? "bg-muted" : "cursor-pointer"}`}
            >
              <h2
                className={`transition-colors duration-200 ${
                  matchType === "upcoming"
                    ? ""
                    : "text-muted-foreground group-hover:text-foreground"
                }`}
              >
                Upcoming
              </h2>
            </div>
            <div
              onClick={() => setMatchType("past")}
              className={`flex-2 group flex items-center justify-center rounded-lg ${matchType === "past" ? "bg-muted" : "cursor-pointer"}`}
            >
              <h2
                className={`transition-colors duration-200 ${
                  matchType === "past"
                    ? ""
                    : "text-muted-foreground group-hover:text-foreground"
                }`}
              >
                Past
              </h2>
            </div>
          </div>
        </div>
        {matchType === "upcoming" ? <Upcoming /> : null}
        {matchType === "live" ? <Live /> : null}
        {matchType === "past" ? <Past /> : null}
      </div>
    </div>
  );
}

export default Matches;

function Live() {
  return (
    <>
      <h1>Live Matches</h1>
      <hr />
      <ul className="mt-3 grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
        {Array.from({ length: 11 }).map((_, i) => (
          <LiveMatch key={i} />
        ))}
      </ul>
    </>
  );
}

function LiveMatch() {
  return (
    <li className="rounded-xl border-2 p-4 py-2">
      <div className="flex">
        <div className="flex-3 space-y-1">
          <div className="mb-2 flex items-center space-x-2">
            <img src={logo} className="h-6 w-6" alt="Logo" />
            <span className="truncate overflow-ellipsis whitespace-nowrap">
              Syracuse University
            </span>
          </div>
          <div className="flex items-center space-x-2 overflow-ellipsis">
            <img src={logo} className="h-6 w-6" alt="Logo" />
            <span className="truncate overflow-ellipsis whitespace-nowrap">
              University of Texas
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
      </div>
      <Button className="bg-secondary text-foreground group mt-2 flex w-full cursor-pointer items-center">
        View
        <ArrowRight
          size={1}
          className="mt-0.5 transition-all group-hover:ml-2"
        />
      </Button>
    </li>
  );
}

function Upcoming() {
  return (
    <>
      <h1>Today</h1>
      <hr />
      <ul className="mt-3 grid grid-cols-1 gap-4 md:grid-cols-2">
        {Array.from({ length: 9 }).map((_, i) => (
          <UpcomingMatch key={i} />
        ))}
      </ul>
      <h1 className="mt-8">This Week</h1>
      <hr />
      <ul className="mt-3 grid grid-cols-1 gap-4 md:grid-cols-2">
        {Array.from({ length: 100 }).map((_, i) => (
          <UpcomingMatch key={i} />
        ))}
      </ul>
    </>
  );
}

function UpcomingMatch() {
  const stars = Math.floor(Math.random() * 5) + 1;
  return (
    <li
      className={`bg-background flex rounded-xl border-2 p-4 py-2 ${stars === 5 ? "drop-shadow-primary/40 border-primary drop-shadow-lg" : ""}`}
    >
      <div className="flex-3 space-y-3">
        <div className="flex items-center space-x-2">
          <img src={logo} className="h-6 w-6" alt="Logo" />
          <span className="truncate overflow-ellipsis whitespace-nowrap">
            Syracuse University
          </span>
          <span className="bg-muted ml-2 flex items-center justify-end rounded-sm text-xs">
            <p className="border-r-1 px-1 font-mono text-xs text-green-500">
              +76
            </p>
            <p className="rounded-sm px-1 font-mono text-xs text-red-500">
              -23
            </p>
          </span>
        </div>
        <div className="flex items-center space-x-2 overflow-ellipsis">
          <img src={logo} className="h-6 w-6" alt="Logo" />
          <span className="truncate overflow-ellipsis whitespace-nowrap">
            University of Texas
          </span>
          <span className="bg-muted ml-2 flex items-center justify-end rounded-sm text-xs">
            <p className="border-r-1 px-1 font-mono text-xs text-green-500">
              +23
            </p>
            <p className="rounded-sm px-1 font-mono text-xs text-red-500">
              -76
            </p>
          </span>
        </div>
      </div>
      <div className="flex-1 text-end text-sm">
        <span className="text-muted-foreground">2025-10-01</span>
        <br />
        <span className="text-muted-foreground">3:00 PM</span>
        <br />
        <span className="text-muted-foreground space-x-.5 mt-1 flex items-center justify-end">
          {Array.from({ length: stars }).map((_, i) => (
            <Star key={i} size={14} className="fill-muted-foreground" />
          ))}
          {Array.from({ length: 5 - stars }).map((_, i) => (
            <Star key={i} size={14} className="text-gray-700" />
          ))}
        </span>
      </div>
    </li>
  );
}

function Past() {
  return (
    <>
      <h1>Yesterday</h1>
      <hr />
      <ul className="mt-3 grid grid-cols-1 gap-4 md:grid-cols-2">
        {Array.from({ length: 5 }).map((_, i) => (
          <Result key={i} />
        ))}
      </ul>
      <h1 className="mt-8">Last Week</h1>
      <hr />
      <ul className="mt-3 grid grid-cols-1 gap-4 md:grid-cols-2">
        {Array.from({ length: 50 }).map((_, i) => (
          <Result key={i} />
        ))}
      </ul>
    </>
  );
}

function Result() {
  return (
    <li className="cursor-pointer rounded-xl border-2 p-4 py-2">
      <div className="flex">
        <div className="flex-3 space-y-2">
          <div className="flex items-center space-x-2">
            <img src={logo} className="h-6 w-6" alt="Logo" />
            <span className="truncate overflow-ellipsis whitespace-nowrap font-semibold">
              Syracuse University
            </span>
            <span className="flex justify-end">
              <p className="ml-2 rounded-sm px-1 font-mono text-xs text-green-500">
                +76
              </p>
            </span>
          </div>
          <div className="flex items-center space-x-2 overflow-ellipsis">
            <img src={logo} className="h-6 w-6" alt="Logo" />
            <span className="text-muted-foreground truncate overflow-ellipsis whitespace-nowrap">
              University of Texas
            </span>
            <span className="flex justify-end">
              <p className="ml-2 rounded-sm px-1 font-mono text-xs text-red-500">
                -76
              </p>
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
      </div>
    </li>
  );
}
