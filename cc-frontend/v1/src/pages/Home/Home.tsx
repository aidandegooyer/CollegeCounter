import LiveMatchesWidget from "./LiveMatchesWidget";
import NewsWidget from "./NewsWidget";
import PlayerRankingsWidget from "./PlayerRankingsWidget";
import ResultsWidget from "./ResultsWidget";
import TeamRankingsWidget from "./TeamRankingsWidget";
import UpcomingMatchesWidget from "./UpcomingMatchesWidget";

function Home() {
  return (
    <div className="home w-full max-w-[1200px]">
      <div
        className="my-4 h-32 w-full rounded-xl border-2"
        style={{
          backgroundPosition: "center", // Change to "top", "bottom", "left", "right", or "center" as needed
          backgroundSize: "cover", // "cover" fills the div, "contain" fits the image, or use specific values
          backgroundRepeat: "no-repeat",
        }}
      >
        <h1 className="pt-10 text-center text-4xl font-bold text-white">
          Welcome to Fall 2025!
        </h1>
      </div>
      <div className="flex w-full space-x-4">
        <div className="flex-1 space-y-4">
          <TeamRankingsWidget />
          <PlayerRankingsWidget />
        </div>
        <div className="flex-2 px-4">
          <NewsWidget />
        </div>
        <div className="flex-1 space-y-4">
          <LiveMatchesWidget />
          <UpcomingMatchesWidget />
          <ResultsWidget />
        </div>
      </div>
    </div>
  );
}

export default Home;
