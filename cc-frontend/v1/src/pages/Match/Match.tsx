import { CountdownTimer } from "@/components/CountdownTimer";
import Logo from "@/components/Logo";
import { Alert, AlertTitle, AlertDescription } from "@/components/ui/alert";
import { Spinner } from "@/components/ui/shadcn-io/spinner";
import { calculateMatchStars } from "@/services/elo";
import { usePublicMatches } from "@/services/hooks";
import { Star } from "lucide-react";
import { useParams } from "react-router";

export function Match() {
  const { id } = useParams<{ id: string }>();

  const { data, isLoading, error } = usePublicMatches({ id });

  const match = data?.results[0];

  const matchDate = match?.date ? new Date(match.date) : null;

  const stars = calculateMatchStars(
    match?.team1.elo || 1000,
    match?.team2.elo || 1000,
  );

  if (isLoading || !data) {
    return (
      <div className="flex h-40 items-center justify-center">
        <Spinner />
      </div>
    );
  }
  if (error || !match) {
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

  return (
    <div className="app-container flex justify-center">
      <div className="w-full max-w-[800px]">
        <div className="mb-8 items-center justify-between sm:flex">
          <span className="flex flex-col items-center justify-center space-x-4">
            <Logo
              src={match.team1.picture}
              className="h-32 w-32 rounded-md"
              alt="Team"
              type="team"
            />
            <div className="flex items-center">
              <h2
                className={`text-center text-xl ${match.score_team1 < match.score_team2 ? "text-muted-foreground" : "text-foreground"}`}
              >
                {match.team1.name}
              </h2>
            </div>
          </span>
          <div className="mx-4 my-4 text-center text-3xl font-bold sm:mt-0">
            {matchDate && match.status === "scheduled" && (
              <CountdownTimer targetDate={matchDate} />
            )}
            {match.status === "completed" && (
              <div className="text-4xl">
                {match.score_team1} - {match.score_team2}
              </div>
            )}
          </div>
          <span className="ml-4 flex flex-col items-center justify-center space-x-4">
            <Logo
              src={match.team2.picture}
              className="h-32 w-32 rounded-md"
              alt="Team"
              type="team"
            />
            <div className="flex items-center">
              <h2
                className={`text-center text-xl ${match.score_team2 < match.score_team1 ? "text-muted-foreground" : "text-foreground"}`}
              >
                {match.team2.name}
              </h2>
            </div>
          </span>
        </div>
        <div className="mx-4 justify-between md:flex">
          <div>
            <h3 className="bg-secondary rounded-xl px-2 py-0.5 text-2xl font-bold">
              {match.competition?.name}
            </h3>
            <div className="justify-center md:flex">
              <span className="text-foreground space-x-.5 mt-1 flex items-center">
                {Array.from({ length: stars }).map((_, i) => (
                  <Star key={i} size={24} className="fill-foreground" />
                ))}
                {Array.from({ length: 5 - stars }).map((_, i) => (
                  <Star key={i} size={24} className="text-gray-700" />
                ))}
              </span>
            </div>
          </div>

          <div className="md:text-right">
            <h3 className="text-2xl font-bold">
              {matchDate &&
                matchDate.toLocaleString("en-US", {
                  hour: "numeric",
                  minute: "2-digit",
                  hour12: true,
                })}
            </h3>
            <h3 className="mb-4 text-2xl font-bold">
              {matchDate &&
                matchDate.toLocaleString("en-US", {
                  month: "long",
                  day: "numeric",
                  year: "numeric",
                })}
            </h3>
          </div>
        </div>
        <h2 className="mt-8 rounded-lg border-2 border-dashed p-2 text-center text-2xl font-bold">
          Match Pages are currently a WIP and will be improved soon!
        </h2>
      </div>
    </div>
  );
}
