import axios from 'axios';
import { getAuth } from 'firebase/auth';

// base API URL
const API_BASE_URL = 'http://127.0.0.1:8000/v1';  // Adjust this according to your setup

const api = axios.create({
  baseURL: API_BASE_URL
});

// Add an interceptor to attach the Firebase auth token to every request TODO: CHANGE THIS TO NOT PUT IT ON ALL REQUESTS
api.interceptors.request.use(async (config) => {
  const auth = getAuth();
  const user = auth.currentUser;

  await new Promise(resolve => setTimeout(resolve, 1000));
  
  if (user) {
    try {
      const token = await user.getIdToken();
      config.headers.Authorization = `Bearer ${token}`;
    } catch (error) {
      console.error('Error getting auth token:', error);
    }
  }
  
  return config;
}, (error) => {
  return Promise.reject(error);
});

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
  participant_matches?: Record<string, string>; // Map of participant_id to team_id
}

export interface ImportMatchesResponse {
  message: string;
  matches_imported: number;
  match_ids: string[];
}

export interface Participant {
  id: string;
  team_id: string | null;
  team_name: string | null;
  competition_id: string | null;
  competition_name: string | null;
  season_id: string | null;
  season_name: string | null;
  faceit_id?: string;
  playfly_id?: string;
  playfly_participant_id?: string;
}

export interface ParticipantMatchRequest {
  participant_id: string;
  team_id: string;
}

/*

ADMIN API FUNCTIONS

*/

// API client functions
export const fetchSeasons = async (): Promise<Season[]> => {
  const response = await api.get(`/seasons/`);
  return response.data;
};

export const createSeason = async (
  name: string, 
  start_date: string, 
  end_date: string
): Promise<Season> => {
  const response = await api.post(`/seasons/create/`, {
    name,
    start_date,
    end_date
  });
  return response.data;
};

export const importMatches = async (
  request: ImportMatchesRequest
): Promise<ImportMatchesResponse> => {
  const response = await api.post(`/import-matches/`, request);
  return response.data;
};

// Database viewer API functions
export const fetchAllTeams = async (): Promise<Team[]> => {
  const response = await api.get(`/teams/`);
  return response.data;
};

export const fetchAllPlayers = async (): Promise<Player[]> => {
  const response = await api.get(`/players/`);
  return response.data;
};

export const fetchAllMatches = async (): Promise<Match[]> => {
  const response = await api.get(`/matches/`);
  return response.data;
};

// Participant matching API functions
export const fetchParticipants = async (): Promise<{participants: Participant[], teams: Team[]}> => {
  const response = await api.get(`/participants/`);
  return response.data;
};

export const matchParticipant = async (
  request: ParticipantMatchRequest
): Promise<{message: string, participant: Participant}> => {
  const response = await api.post(`/participants/`, request);
  return response.data;
};

// Database clearing API function
export const clearDatabase = async (
  securityKey: string
): Promise<{message: string}> => {
  const response = await api.post(`/clear-database/`, {
    security_key: securityKey
  });
  return response.data;
};

// fetch data from Faceit API
export const fetchFaceitMatches = async (eventId: string): Promise<any> => {
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

    if (items.length < limit) {
      hasMore = false;
    } else {
      offset += limit;
    }
  }

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


/*

CLIENT API FUNCTIONS

*/

// Public API interfaces
export interface PaginatedResponse<T> {
  count: number;
  total_pages: number;
  current_page: number;
  page_size: number;
  results: T[];
}

export interface PublicTeam {
  id: string;
  name: string;
  picture?: string;
  school_name?: string;
  elo: number;
  captain?: {
    id: string;
    name: string;
    picture?: string;
  };
}

export interface PublicPlayer {
  id: string;
  name: string;
  picture?: string;
  skill_level: number;
  steam_id?: string;
  faceit_id?: string;
  elo: number;
  team?: {
    id: string;
    name: string;
    picture?: string;
  };
  benched: boolean;
  visible: boolean;
}

export interface PublicMatch {
  id: string;
  team1: {
    id: string;
    name: string;
    picture?: string;
  };
  team2: {
    id: string;
    name: string;
    picture?: string;
  };
  date: string;
  status: string;
  url?: string;
  winner?: {
    id: string;
    name: string;
    picture?: string;
  };
  score_team1: number;
  score_team2: number;
  platform: string;
  competition?: {
    id: string;
    name: string;
  };
  season?: {
    id: string;
    name: string;
  };
}

export interface PublicSeason {
  id: string;
  name: string;
  start_date: string;
  end_date: string;
  is_current: boolean;
}

// Public API query parameters
export interface TeamQueryParams {
  id?: string | string[];
  name?: string;
  school_name?: string;
  season_id?: string;
  competition_id?: string;
  page?: number;
  page_size?: number;
  sort?: 'name' | 'school_name' | 'elo';
  order?: 'asc' | 'desc';
}

export interface PlayerQueryParams {
  id?: string | string[];
  name?: string;
  team_id?: string;
  steam_id?: string;
  faceit_id?: string;
  visible?: boolean;
  benched?: boolean;
  page?: number;
  page_size?: number;
  sort?: 'name' | 'elo' | 'skill_level';
  order?: 'asc' | 'desc';
}

export interface MatchQueryParams {
  id?: string | string[];
  team_id?: string;
  status?: 'scheduled' | 'in_progress' | 'completed' | 'cancelled';
  platform?: 'faceit' | 'playfly';
  date_from?: string;
  date_to?: string;
  season_id?: string;
  competition_id?: string;
  page?: number;
  page_size?: number;
  sort?: 'date' | 'status';
  order?: 'asc' | 'desc';
}

export interface SeasonQueryParams {
  id?: string | string[];
  current?: boolean;
  page?: number;
  page_size?: number;
  sort?: 'name' | 'start_date' | 'end_date';
  order?: 'asc' | 'desc';
}

// Helper function to convert query params to URL search params
const convertToQueryString = (params: Record<string, any>): string => {
  const searchParams = new URLSearchParams();
  
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== null) {
      if (Array.isArray(value)) {
        searchParams.append(key, value.join(','));
      } else if (typeof value === 'boolean') {
        searchParams.append(key, value.toString());
      } else {
        searchParams.append(key, String(value));
      }
    }
  });
  
  return searchParams.toString();
};

// Public API client functions
export const fetchPublicTeams = async (params: TeamQueryParams = {}): Promise<PaginatedResponse<PublicTeam>> => {
  const queryString = convertToQueryString(params);
  const response = await api.get(`/public/teams${queryString ? `?${queryString}` : ''}`);
  return response.data;
};

export const fetchPublicPlayers = async (params: PlayerQueryParams = {}): Promise<PaginatedResponse<PublicPlayer>> => {
  const queryString = convertToQueryString(params);
  const response = await api.get(`/public/players${queryString ? `?${queryString}` : ''}`);
  return response.data;
};

export const fetchPublicMatches = async (params: MatchQueryParams = {}): Promise<PaginatedResponse<PublicMatch>> => {
  const queryString = convertToQueryString(params);
  const response = await api.get(`/public/matches${queryString ? `?${queryString}` : ''}`);
  return response.data;
};

export const fetchPublicSeasons = async (params: SeasonQueryParams = {}): Promise<PaginatedResponse<PublicSeason>> => {
  const queryString = convertToQueryString(params);
  const response = await api.get(`/public/seasons${queryString ? `?${queryString}` : ''}`);
  return response.data;
};


// Legacy function - consider deprecating or updating to use public API
export const fetchTeams = async (): Promise<Team[]> => {
  const response = await api.get(`/teams/`);
  return response.data;
}