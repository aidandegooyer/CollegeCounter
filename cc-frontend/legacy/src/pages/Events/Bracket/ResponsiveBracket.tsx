import React from "react";
import {
  Bracket,
  Seed,
  SeedItem,
  SeedTeam,
  IRenderSeedProps,
  SeedTime,
} from "react-brackets";
import { useQueries, useQuery } from "@tanstack/react-query";
import { EventMatch, Match, Team } from "../../../types";
import { Link } from "react-router-dom";

const apiBaseUrl =
  import.meta.env.VITE_API_BASE_URL || "https://api.collegecounter.org";

const fetchMatch = async (match_id: string): Promise<Match> => {
  const response = await fetch(`${apiBaseUrl}/match/${match_id}`);
  return response.json();
};

const fetchTeam = async (team_id: string): Promise<Team> => {
  const response = await fetch(`${apiBaseUrl}/team/${team_id}`);
  return response.json();
};

const fetchByeTeam = async (team_id: string): Promise<Team> => {
  if (team_id === "BYE") {
    return { name: "---", team_id: "BYE", elo: 0, leader: "", avatar: "" };
  }
  const response = await fetch(`${apiBaseUrl}/team_by_pfid/${team_id}`);
  return response.json();
};

// A custom seed renderer to display team names and scores
const CustomSeed = ({ seed, breakpoint }: IRenderSeedProps) => {
  const team1_id = seed.teams[0]?.name;
  const team2_id = seed.teams[1]?.name;

  if (!team1_id || !team2_id) {
    return (
      <Seed mobileBreakpoint={breakpoint} style={{ fontSize: 12 }}>
        <SeedItem>
          <SeedTeam>---</SeedTeam>
          <SeedTeam>---</SeedTeam>
        </SeedItem>
      </Seed>
    );
  }

  const fetchTeam1 = team2_id === "BYE" ? fetchByeTeam : fetchTeam;

  const {
    data: team1,
    isLoading: team1Loading,
    error: team1ErrorObj,
    isError: team1Error,
  } = useQuery<Team>({
    queryKey: ["team", team1_id],
    queryFn: () => fetchTeam1(team1_id!),
    staleTime: 1000 * 60 * 10,
  });

  const fetchTeam2 = team2_id === "BYE" ? fetchByeTeam : fetchTeam;

  const {
    data: team2,
    isLoading: team2Loading,
    error: team2ErrorObj,
    isError: team2Error,
  } = useQuery<Team>({
    queryKey: ["team", team2_id],
    queryFn: () => fetchTeam2(team2_id!),
    staleTime: 1000 * 60 * 10,
  });
  if (team1Loading || team2Loading) {
    return (
      <Seed mobileBreakpoint={breakpoint} style={{ fontSize: 12 }}>
        <SeedItem>Loading teams…</SeedItem>{" "}
      </Seed>
    );
  }
  if (team1Error || team2Error) {
    return (
      <Seed mobileBreakpoint={breakpoint} style={{ fontSize: 12 }}>
        <SeedItem>
          Error loading team details.{" "}
          {team1ErrorObj?.message || team2ErrorObj?.message || ""}
        </SeedItem>{" "}
      </Seed>
    );
  }

  return (
    <Seed mobileBreakpoint={breakpoint} style={{ fontSize: 12 }}>
      <SeedItem>
        <div style={{ width: "250px" }}>
          <div style={{ display: "flex", justifyContent: "space-between" }}>
            <SeedTeam>
              {team1?.name !== "---" ? (
                <Link
                  to={`/team?id=${team1?.team_id}`}
                  style={{
                    color:
                      seed.teams[0]?.score >= seed.teams[1]?.score
                        ? "white"
                        : "grey",
                  }}
                >
                  {team1?.name}
                </Link>
              ) : (
                "---"
              )}
            </SeedTeam>
            <span style={{ marginTop: "5px", marginRight: "10px" }}>
              {seed.teams[0]?.score ?? "-"}
            </span>
          </div>
          <div style={{ display: "flex", justifyContent: "space-between" }}>
            <SeedTeam>
              {team2?.name !== "---" ? (
                <Link
                  to={`/team?id=${team2?.team_id}`}
                  style={{
                    color:
                      seed.teams[1]?.score >= seed.teams[0]?.score
                        ? "white"
                        : "grey",
                  }}
                >
                  {team2?.name}
                </Link>
              ) : (
                "---"
              )}
            </SeedTeam>
            <span style={{ marginTop: "5px", marginRight: "10px" }}>
              {seed.teams[1]?.score ?? "-"}
            </span>
          </div>
        </div>
        <SeedTime>{team2_id === "BYE" ? "" : seed.date}</SeedTime>
      </SeedItem>
    </Seed>
  );
};

// Helper function: convert a Unix timestamp (in seconds) to a date string
const convertTimestampToDate = (ts: number) =>
  new Date(ts * 1000).toDateString();

// Interfaces for the bracket data format
interface SeedData {
  id: string;
  date: string;
  teams: { name: string; score: number | null }[];
}

interface BracketRound {
  title: string;
  seeds: SeedData[];
}

// This function groups the event matches by round and converts them into the seed format
const convertMatchesToBracketData = (
  eventMatches: EventMatch[],
  matchDetails: Record<string, any>
): BracketRound[] => {
  // Create a sorted copy of eventMatches so that seeds are in the proper order.
  const sortedMatches = [...eventMatches].sort(
    (a, b) => a.number_in_bracket - b.number_in_bracket
  );

  const roundsMap: Record<string, SeedData[]> = {};

  sortedMatches.forEach((match) => {
    const roundTitle = match.round;
    const detail = match.match_id ? matchDetails[match.match_id] : null;
    if (!detail) return;
    let seed: SeedData;
    if (match.isbye) {
      seed = {
        id: detail.match_id,
        date: convertTimestampToDate(detail.scheduled_time),
        teams: [
          { name: match.bye_team_id, score: null },
          { name: "BYE", score: null },
        ],
      };
    } else {
      seed = {
        id: detail.match_id,
        date: convertTimestampToDate(detail.scheduled_time),
        teams: [
          {
            name: detail.team1_id || "",
            score: detail.results_score_team1 ?? null,
          },
          {
            name: detail.team2_id || "",
            score: detail.results_score_team2 ?? null,
          },
        ],
      };
    }
    if (!roundsMap[roundTitle]) {
      roundsMap[roundTitle] = [];
    }
    roundsMap[roundTitle].push(seed);
  });

  // Sort round titles by extracting a number (if your rounds are titled like "Round 1", "Round 2", etc.)
  const sortedTitles = Object.keys(roundsMap).sort((a, b) => {
    const numA = parseInt(a.split(" ")[1]) || 0;
    const numB = parseInt(b.split(" ")[1]) || 0;
    return numA - numB;
  });

  return sortedTitles.map((title) => ({
    title,
    seeds: roundsMap[title],
  }));
};

interface ResponsiveBracketProps {
  matches: EventMatch[];
}

const ResponsiveBracket: React.FC<ResponsiveBracketProps> = ({ matches }) => {
  // Use TanStack Query's useQueries to fetch match details for each event match
  const matchQueries = useQueries({
    queries: matches.map((match) => ({
      queryKey: ["match", match.match_id],
      queryFn: () =>
        match.match_id
          ? fetchMatch(match.match_id)
          : Promise.reject("Match ID is undefined"),
      staleTime: 1000 * 60 * 10,
    })),
  });

  // Show a loading state while any query is still loading
  if (matchQueries.some((q) => q.isLoading)) {
    return <div>Loading matches…</div>;
  }
  // Show an error state if any query encountered an error
  if (matchQueries.some((q) => q.error)) {
    return <div>Error loading match details.</div>;
  }

  // Build a mapping of match_id to match detail data
  const matchDetails: Record<string, any> = {};
  matches.forEach((match, index) => {
    if (match.match_id) {
      matchDetails[match.match_id] = matchQueries[index].data;
    }
  });

  // Convert the original event matches and fetched match details into bracketData format
  const bracketData = convertMatchesToBracketData(matches, matchDetails);

  interface BlankSeed {
    id: string;
    date: string;
    teams: { name: string; score: number | null }[];
  }

  interface BracketRound {
    title: string;
    seeds: BlankSeed[];
  }

  function autofillBracket(initialBracket: BracketRound[]): BracketRound[] {
    // Copy the initial rounds.
    const result = [...initialBracket];
    if (result.length === 0) return result;

    // Get the number of seeds in the last round.
    let lastRound = result[result.length - 1];
    let roundNumber = result.length + 1;
    let currentCount = lastRound.seeds.length;

    // Generate rounds until only one seed remains.
    while (currentCount > 1) {
      const nextCount = Math.ceil(currentCount / 2);
      const blankSeeds: BlankSeed[] = [];

      for (let i = 0; i < nextCount; i++) {
        blankSeeds.push({
          id: `placeholder-Round ${roundNumber}-${i}`,
          date: "", // You can add a default or leave blank.
          teams: [
            { name: "", score: null },
            { name: "", score: null },
          ],
        });
      }

      result.push({
        title: `Round ${roundNumber}`,
        seeds: blankSeeds,
      });

      currentCount = nextCount;
      roundNumber++;
    }

    return result;
  }

  const fullBracketData = autofillBracket(bracketData);

  return (
    <Bracket
      rounds={fullBracketData}
      mobileBreakpoint={0}
      renderSeedComponent={CustomSeed}
    />
  );
};

export default ResponsiveBracket;
