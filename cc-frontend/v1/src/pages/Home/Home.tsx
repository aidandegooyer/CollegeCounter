import LiveMatchesWidget from "./LiveMatchesWidget";
import NewsWidget from "./NewsWidget";
import PlayerRankingsWidget from "./PlayerRankingsWidget";
import ResultsWidget from "./ResultsWidget";
import TeamRankingsWidget from "./TeamRankingsWidget";
import UpcomingMatchesWidget from "./UpcomingMatchesWidget";
import c4_logo from "@/assets/c4 title noborder.svg";
import { NavLink } from "react-router";

function Home() {
  document.title = "College Counter";
  return (
    <div className="app-container mx-4 mt-2 flex justify-center">
      <div className="home w-full max-w-[1200px]">
        <NavLink to="/events">
          <div className="grid grid-cols-5 gap-4">
            <div className="col-span-5 my-4 flex h-32 w-full flex-col items-center justify-center rounded-xl border-2 md:col-span-3">
              <img src={c4_logo} alt="C4 Logo" className="-m-3 h-24" />
              <h1 className="flex items-center text-3xl">
                Returns for January!
              </h1>
            </div>
            <div className="col-span-2 my-4 hidden h-32 w-full flex-col items-center justify-center rounded-xl border-2 md:flex">
              <h1 className="flex items-center text-3xl">
                Previous Champions:
              </h1>
              <img
                src={
                  "https://distribution.faceit-cdn.net/images/c27cbea5-0656-4d72-ab92-581b0c29abb2.jpg"
                }
                alt="C4 Logo"
                className="h-16 w-16 rounded-md"
              />
              <h1 className="flex items-center text-xl">Ashland Eagles</h1>
            </div>
          </div>
        </NavLink>
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
