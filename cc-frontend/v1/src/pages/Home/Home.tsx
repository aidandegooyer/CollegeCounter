import LiveMatchesWidget from "./LiveMatchesWidget";
import NewsWidget from "./NewsWidget";
import PlayerRankingsWidget from "./PlayerRankingsWidget";
import ResultsWidget from "./ResultsWidget";
import TeamRankingsWidget from "./TeamRankingsWidget";
import UpcomingMatchesWidget from "./UpcomingMatchesWidget";

function Home() {
  document.title = "College Counter";
  return (
    <div className="app-container mx-4 mt-2 flex justify-center">
      <div className="home w-full max-w-[1200px]">
        <div
          className="my-4 flex h-32 w-full items-center justify-center rounded-xl border-2"
          style={{
            backgroundPosition: "center", // Change to "top", "bottom", "left", "right", or "center" as needed
            backgroundSize: "cover", // "cover" fills the div, "contain" fits the image, or use specific values
            backgroundRepeat: "no-repeat",
          }}
        >
          <h1 className="text-center text-4xl font-bold sm:text-6xl">
            Welcome to Fall 2026!
          </h1>
        </div>
        <div className="hidden w-full sm:flex">
          <div className="mr-8 hidden flex-1 space-y-4 lg:block">
            <TeamRankingsWidget />
            <PlayerRankingsWidget />
          </div>
          <div className="flex-2">
            <NewsWidget post_count={8} />
          </div>
          <div className="ml-8 hidden flex-1 space-y-4 md:block">
            <LiveMatchesWidget />
            <UpcomingMatchesWidget />
            <ResultsWidget />
          </div>
        </div>
        <div className="flex w-full flex-col justify-center space-y-4 sm:hidden">
          <UpcomingMatchesWidget limit={2} />
          <ResultsWidget limit={2} />
          <NewsWidget post_count={2} />
        </div>
      </div>
    </div>
  );
}

export default Home;
