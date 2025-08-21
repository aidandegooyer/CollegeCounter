import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group";
import { Label } from "@/components/ui/label";

import { useState } from "react";
import TeamRankingComponent from "./TeamRankingComponent";
import PlayerRankingComponent from "./PlayerRankingComponent";

function Rankings() {
  var initRankingType = "team";
  const hash = window.location.hash.replace("#", "");
  if (hash === "team" || hash === "player") {
    initRankingType = hash;
  }

  const [rankingType, setRankingType] = useState(initRankingType || "team");

  return (
    <div className="app-container mx-16 flex justify-center">
      <div className="rankings w-full max-w-[1200px] justify-center">
        <div className="flex justify-center">
          <div className="my-4 flex h-12 w-[500px] rounded-xl border-2">
            <div
              onClick={() => setRankingType("team")}
              className={`group flex flex-1 items-center justify-center rounded-lg ${rankingType === "team" ? "bg-muted" : "cursor-pointer"}`}
            >
              <h2
                className={`transition-colors duration-200 ${
                  rankingType === "team"
                    ? ""
                    : "text-muted-foreground group-hover:text-foreground"
                }`}
              >
                Team Rankings
              </h2>
            </div>
            <div
              onClick={() => setRankingType("player")}
              className={`group flex flex-1 items-center justify-center rounded-lg ${rankingType === "player" ? "bg-muted" : "cursor-pointer"}`}
            >
              <h2
                className={`transition-colors duration-200 ${
                  rankingType === "player"
                    ? ""
                    : "text-muted-foreground group-hover:text-foreground"
                }`}
              >
                Player Rankings
              </h2>
            </div>
          </div>
        </div>
        <h1>Ranking on ##-##-####</h1>
        <div className="mt-2 flex w-full">
          <div className="flex-4 space-y-3">
            {Array.from({ length: 50 }).map((_, i) =>
              rankingType === "player" ? (
                <PlayerRankingComponent key={i} />
              ) : (
                <TeamRankingComponent key={i} />
              ),
            )}
          </div>
          <div className="ml-8 hidden flex-1 space-y-4 lg:block">
            {rankingType === "team" ? (
              <TeamRankingsFilter />
            ) : (
              <PlayerRankingsFilter />
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

export default Rankings;

function TeamRankingsFilter() {
  return (
    <div className="team-rankings-filter w-full rounded-xl border-2 p-4 py-2">
      <h2>Filter</h2>
      <hr />
      <h3 className="mt-2">Competition</h3>
      <RadioGroup className="my-2" defaultValue="all">
        <Label className="flex cursor-pointer space-x-2">
          <RadioGroupItem value="all" id="competition-all" />
          <span className="">All</span>
        </Label>
        <Label className="flex cursor-pointer space-x-2">
          <RadioGroupItem value="necc" id="competition-necc" />
          <span className="">NECC</span>
        </Label>
        <Label className="flex cursor-pointer space-x-2">
          <RadioGroupItem value="playfly" id="competition-playfly" />
          <span className="">Playfly</span>
        </Label>
      </RadioGroup>
    </div>
  );
}

function PlayerRankingsFilter() {
  return (
    <div className="team-rankings-filter w-full rounded-xl border-2 p-4 py-2">
      <h2>Filter</h2>
      <hr />
      <h3 className="mt-2">Competition</h3>
      <RadioGroup className="my-2" defaultValue="all">
        <Label className="flex cursor-pointer space-x-2">
          <RadioGroupItem value="all" id="competition-all" />
          <span className="">All</span>
        </Label>
        <Label className="flex cursor-pointer space-x-2">
          <RadioGroupItem value="necc" id="competition-necc" />
          <span className="">NECC</span>
        </Label>
        <Label className="flex cursor-pointer space-x-2">
          <RadioGroupItem value="playfly" id="competition-playfly" />
          <span className="">Playfly</span>
        </Label>
      </RadioGroup>
    </div>
  );
}
