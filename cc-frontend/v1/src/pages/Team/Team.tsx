import Logo from "@/components/Logo";
import {
  usePublicEvents,
  usePublicTeams,
  useTeamRanking,
} from "@/services/hooks";
import { useParams } from "react-router";
import TeamMatches from "./TeamMatches";
import TeamRoster from "./TeamRoster";
import TeamRankingGraph from "./TeamRankingGraph";
import { Alert, AlertTitle, AlertDescription } from "@/components/ui/alert";
import { Spinner } from "@/components/ui/shadcn-io/spinner";
import { CompetitionLabel } from "@/components/CompetitionLabel";
import { Link } from "react-router";
import { Trophy } from "lucide-react";
import { useDocumentTitle } from "@/hooks/useDocumentTitle";

export function Team() {
  const { id } = useParams<{ id: string }>();

  const { data, isLoading, error } = usePublicTeams({ id });
  const team = data?.results[0];
  useDocumentTitle(team?.name ?? "Team");

  const {
    data: rankingData,
    isLoading: rankingIsLoading,
    error: rankingError,
  } = useTeamRanking({
    team_id: id,
  });

  const RankingDate = rankingData?.ranking.date
    ? new Date(rankingData.ranking.date)
    : null;
  if (isLoading || !data) {
    return (
      <div className="flex h-40 items-center justify-center">
        <Spinner />
      </div>
    );
  }
  if (error || !team) {
    return (
      <div className="mt-4">
        <Alert variant="destructive" className="mt-4">
          <AlertTitle className="text-lg">Error</AlertTitle>
          <AlertDescription>
            There was an error loading the team. Please try again later.
          </AlertDescription>
        </Alert>
      </div>
    );
  }

  const uniqueCompetitions = Array.from(
    new Map(
      (team.current_competitions || [])
        .filter((comp) => comp.name && !comp.name.includes("(p)"))
        .map((comp) => [comp.name, comp]),
    ).values(),
  );

  return (
    <div className="app-container flex justify-center">
      <div className="w-full max-w-[800px]">
        <div className="mb-8 items-center justify-between sm:flex">
          <span className="ml-4 flex items-center space-x-4">
            <Logo
              src={team.picture}
              className="h-32 w-32 rounded-md"
              alt="Team"
              type="team"
            />
            <div>
              <h2 className="text-4xl">{team.name}</h2>
              <TrophycaseLogos teamId={id} />
              <h4 className="text-muted-foreground text-lg">
                {team.school_name}
              </h4>
              <div className="mt-2 flex flex-wrap gap-2">
                {uniqueCompetitions.map((comp) => (
                  <CompetitionLabel key={comp.name} competition={comp.name} />
                ))}
              </div>
            </div>
          </span>
          <div className="mt-4 mr-8 ml-4 sm:mt-0 sm:text-right">
            <h2 className="text-6xl">
              #
              {rankingData ? (
                rankingData.rank
              ) : rankingIsLoading ? (
                <Spinner />
              ) : rankingError ? (
                "N/A"
              ) : (
                "-"
              )}
            </h2>
            <p className="text-muted-foreground">
              Ranking as of{" "}
              {rankingData ? RankingDate?.toLocaleDateString() : "-"}
            </p>
          </div>
        </div>

        {id && <TeamRoster teamId={id} />}

        {/* key resets the picked season when navigating between teams */}
        {id && <TeamRankingGraph key={id} teamId={id} />}

        {/* <Trophycase teamId={id} /> */}

        {id && <TeamMatches teamId={id} />}
      </div>
    </div>
  );
}

interface TrophycaseProps {
  teamId?: string;
}

interface EventTrophyLogoProps {
  eventName: string;
  eventPicture?: string;
  className: string;
}

function EventTrophyLogo({
  eventName,
  eventPicture,
  className,
}: EventTrophyLogoProps) {
  return (
    <span className="relative block">
      <Logo
        src={eventPicture}
        className={className}
        alt={eventName}
        type="team"
      />
      <Trophy
        className="absolute right-0 bottom-0 h-4 w-4 text-yellow-500"
        aria-hidden="true"
      />
    </span>
  );
}

function TrophycaseLogos({ teamId }: TrophycaseProps) {
  const { data, isLoading, error } = usePublicEvents(
    {
      winner_id: teamId,
      trophycase: true,
      page_size: 100,
      sort: "start_date",
      order: "desc",
    },
    {
      enabled: Boolean(teamId),
    },
  );

  if (!teamId) return null;

  if (isLoading) {
    return (
      <div className="mt-2" aria-label="Loading trophy case">
        <Spinner className="h-4 w-4" />
      </div>
    );
  }

  if (error) {
    return (
      <Alert variant="destructive" className="mt-2">
        <AlertTitle>Error</AlertTitle>
        <AlertDescription>
          There was an error loading the trophy case. Please try again later.
        </AlertDescription>
      </Alert>
    );
  }

  const trophies = data?.results ?? [];
  if (trophies.length === 0) return null;

  return (
    <div className="mt-2 flex flex-wrap gap-1.5" aria-label="Trophy case">
      {trophies.map((event) => (
        <Link
          key={event.id}
          to={`/events/${event.id}`}
          className="group block rounded p-0.5"
          title={`${event.name} Champions`}
          aria-label={event.name}
        >
          <EventTrophyLogo
            eventPicture={event.picture}
            eventName={event.name}
            className="h-12 w-12 rounded object-contain transition-transform group-hover:scale-110"
          />
        </Link>
      ))}
    </div>
  );
}
