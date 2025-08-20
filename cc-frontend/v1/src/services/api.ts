import axios from 'axios';

// Define the base API URL
const API_BASE_URL = 'http://127.0.0.1:8000/v1';  // Adjust this according to your setup

// API interfaces
export interface Season {
  id: string;
  name: string;
  start_date: string;
  end_date: string;
}

export interface Team {
  id: string;
  name: string;
  picture?: string;
  school_name?: string;
  elo: number;
  captain?: Player;
}

export interface Player {
  id: string;
  name: string;
  picture?: string;
  skill_level: number;
  steam_id?: string;
  faceit_id?: string;
  elo: number;
  team?: Team;
  benched: boolean;
  visible: boolean;
}

export interface Match {
  id: string;
  team1: Team;
  team2: Team;
  date: string;
  status: string;
  url?: string;
  winner?: Team;
  score_team1: number;
  score_team2: number;
  platform: string;
}

export interface ImportMatchesRequest {
  platform: 'faceit' | 'playfly';
  competition_name: string;
  season_id: string;
  data: any; // The raw API response data
}

export interface ImportMatchesResponse {
  message: string;
  matches_imported: number;
  match_ids: string[];
}

// API client functions
export const fetchSeasons = async (): Promise<Season[]> => {
  const response = await axios.get(`${API_BASE_URL}/seasons/`);
  return response.data;
};

export const createSeason = async (
  name: string, 
  start_date: string, 
  end_date: string
): Promise<Season> => {
  const response = await axios.post(`${API_BASE_URL}/seasons/create/`, {
    name,
    start_date,
    end_date
  });
  return response.data;
};

export const importMatches = async (
  request: ImportMatchesRequest
): Promise<ImportMatchesResponse> => {
  const response = await axios.post(`${API_BASE_URL}/import-matches/`, request);
  return response.data;
};

// Database viewer API functions
export const fetchTeams = async (): Promise<Team[]> => {
  const response = await axios.get(`${API_BASE_URL}/teams/`);
  return response.data;
};

export const fetchPlayers = async (): Promise<Player[]> => {
  const response = await axios.get(`${API_BASE_URL}/players/`);
  return response.data;
};

export const fetchMatches = async (): Promise<Match[]> => {
  const response = await axios.get(`${API_BASE_URL}/matches/`);
  return response.data;
};

// Function to fetch data from Faceit API
export const fetchFaceitMatches = async (eventId: string): Promise<any> => {
  const apiKey = import.meta.env.VITE_FACEIT_API_KEY;
  const limit = 100;
  let offset = 0;
  let allItems: any[] = [];
  let hasMore = true;

  while (hasMore) {
    const response = await axios.get(
      `https://open.faceit.com/data/v4/championships/${eventId}/matches`,
      {
        headers: {
          'Authorization': `Bearer ${"3c0ddd87-ff50-45df-8d56-3cf62ef5fbc8"}`,
        },
        params: {
          offset,
          limit,
        },
      }
    );
    const data = response.data;
    const items = data.items || [];
    allItems = allItems.concat(items);

    // If fewer than limit items are returned, we've reached the end
    if (items.length < limit) {
      hasMore = false;
    } else {
      offset += limit;
    }
  }

  // Return in the same structure as a single response
  return {
    ...((allItems.length && { items: allItems }) || { items: [] }),
  };
};

// Function to fetch data from Playfly API
export const fetchPlayflyMatches = async (eventId: string): Promise<any> => {
  // Implement based on Playfly API documentation
  // This is a placeholder
  const response = await axios.get(`https://api.playfly.com/events/${eventId}/matches`);
  return response.data;
};
