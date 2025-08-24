import { useState } from "react";
import type { PublicTeam, Team } from "@/services/api";
import { usePublicPlayers } from "@/services/hooks";
import { Spinner } from "@/components/ui/shadcn-io/spinner";
import Logo from "@/components/Logo";

interface TeamRankingComponentProps {
  team: PublicTeam;
  rank: number;
}

function TeamRankingComponent(props: TeamRankingComponentProps) {
  const [expanded, setExpanded] = useState(false);

  const { data, error, isLoading } = usePublicPlayers(
    {
      team_id: props.team.id,
      sort: "elo",
      order: "desc",
      visible: true,
      benched: false,
      page_size: 5,
    },
    { enabled: expanded },
  );

  function expandedCard() {
    if (isLoading)
      return (
        <div className="flex h-40 items-center justify-center">
          <Spinner></Spinner>
        </div>
      );
    if (error || data == undefined) return <div>Error loading players</div>;

    return (
      <div className="mx-12 flex justify-between pt-3">
        {data.results.map((player, i) => (
          <div key={i}>
            <Logo
              src={player.picture}
              className="h-32 w-32"
              alt="Player"
              type="player"
            />
            <p className="border-t-2 text-center">{player.name}</p>
          </div>
        ))}
      </div>
    );
  }

  return (
    <div
      className={
        "team-ranking-component w-full cursor-pointer rounded-xl border-2 p-2 pl-4"
      }
      onClick={() => setExpanded(!expanded)}
    >
      <div className="flex justify-between">
        <div className="flex items-center space-x-2">
          <span className="mr-3 text-end font-mono text-xl">
            {props.rank + 1}
          </span>
          <Logo
            src={props.team.picture}
            className="h-8 w-8 rounded-sm"
            alt="pfp"
            type="team"
          />
          <span className="truncate overflow-ellipsis whitespace-nowrap text-xl">
            {props.team.name}
          </span>
        </div>
        <div>
          <div className="bg-secondary drop-shadow-secondary drop-shadow-lg/50 rounded-md p-1 px-2 font-mono text-lg">
            {props.team.elo}
          </div>
        </div>
      </div>
      <div
        className={`hidden transition-all duration-300 md:block ${expanded ? "h-[165px]" : "h-0 overflow-hidden"}`}
      >
        <div
          className={`bg-background z-10 transition-all duration-300 ${expanded ? "opacity-100" : "opacity-0"}`}
        >
          {expandedCard()}
        </div>
      </div>
    </div>
  );
}

export default TeamRankingComponent;
