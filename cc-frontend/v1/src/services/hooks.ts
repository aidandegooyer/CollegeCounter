import { useQuery } from '@tanstack/react-query';
import { 
  fetchPublicTeams, 
  fetchPublicPlayers, 
  fetchPublicMatches, 
  fetchPublicSeasons,
  fetchPublicRankings,
  fetchPublicRankingItems,
} from '@/services/api';
import type {
  TeamQueryParams,
  PlayerQueryParams,
  MatchQueryParams,
  SeasonQueryParams,
  RankingQueryParams,
  RankingItemQueryParams
} from '@/services/api';




// API HOOKS

const DEFAULT_STALE_TIME = 1000 * 60 * 5;

export function usePublicTeams(params: TeamQueryParams = {}, options = {}) {
  return useQuery({
    queryKey: ['public', 'teams', params],
    queryFn: () => fetchPublicTeams(params),
    staleTime: DEFAULT_STALE_TIME,
    ...options,
  });
}

export function usePublicPlayers(params: PlayerQueryParams = {}, options = {}) {
  return useQuery({
    queryKey: ['public', 'players', params],
    queryFn: () => fetchPublicPlayers(params),
    staleTime: DEFAULT_STALE_TIME,
    ...options,
  });
}

export function usePublicMatches(params: MatchQueryParams = {}, options = {}) {
  return useQuery({
    queryKey: ['public', 'matches', params],
    queryFn: () => fetchPublicMatches(params),
    staleTime: DEFAULT_STALE_TIME,
    ...options,
  });
}

export function usePublicSeasons(params: SeasonQueryParams = {}, options = {}) {
  return useQuery({
    queryKey: ['public', 'seasons', params],
    queryFn: () => fetchPublicSeasons(params),
    staleTime: DEFAULT_STALE_TIME,
    ...options,
  });
}

export function usePublicRankings(params: RankingQueryParams = {}, options = {}) {
  return useQuery({
    queryKey: ['public', 'rankings', params],
    queryFn: () => fetchPublicRankings(params),
    staleTime: DEFAULT_STALE_TIME,
    ...options,
  });
}

export function usePublicRankingItems(params: RankingItemQueryParams, options = {}) {
  return useQuery({
    queryKey: ['public', 'ranking-items', params],
    queryFn: () => fetchPublicRankingItems(params),
    staleTime: DEFAULT_STALE_TIME,
    enabled: !!params.ranking_id, // Only fetch if ranking_id is provided
    ...options,
  });
}
// end of full-featured API hooks

// hooks for common queries
export function useCurrentSeason(options = {}) {
  return useQuery({
    queryKey: ['public', 'seasons', 'current'],
    queryFn: () => fetchPublicSeasons({ current: true, page_size: 1 }),
    staleTime: DEFAULT_STALE_TIME,
    select: (data) => data.results[0] || null,
    ...options,
  });
}

export function useTeamDetails(teamId: string | undefined, options = {}) {
  return useQuery({
    queryKey: ['public', 'teams', teamId],
    queryFn: () => fetchPublicTeams({ id: teamId }),
    staleTime: DEFAULT_STALE_TIME,
    select: (data) => data.results[0] || null,
    enabled: !!teamId,
    ...options,
  });
}

export function usePlayerDetails(playerId: string | undefined, options = {}) {
  return useQuery({
    queryKey: ['public', 'players', playerId],
    queryFn: () => fetchPublicPlayers({ id: playerId }),
    staleTime: DEFAULT_STALE_TIME,
    select: (data) => data.results[0] || null,
    enabled: !!playerId,
    ...options,
  });
}

export function useTeamMatches(teamId: string | undefined, options = {}) {
  return useQuery({
    queryKey: ['public', 'matches', 'team', teamId],
    queryFn: () => fetchPublicMatches({ team_id: teamId, sort: 'date', order: 'desc' }),
    staleTime: DEFAULT_STALE_TIME,
    enabled: !!teamId,
    ...options,
  });
}

export function useTeamPlayers(teamId: string | undefined, options = {}) {
  return useQuery({
    queryKey: ['public', 'players', 'team', teamId],
    queryFn: () => fetchPublicPlayers({ team_id: teamId, visible: true }),
    staleTime: DEFAULT_STALE_TIME,
    enabled: !!teamId,
    ...options,
  });
}

export function useRecentMatches(limit = 5, options = {}) {
  return useQuery({
    queryKey: ['public', 'matches', 'recent', limit],
    queryFn: () => fetchPublicMatches({ 
      sort: 'date', 
      order: 'desc', 
      page_size: limit,
      status: 'completed'
    }),
    staleTime: DEFAULT_STALE_TIME,
    ...options,
  });
}

export function useUpcomingMatches(limit = 5, options = {}) {
  return useQuery({
    queryKey: ['public', 'matches', 'upcoming', limit],
    queryFn: () => fetchPublicMatches({ 
      sort: 'date', 
      order: 'asc', 
      page_size: limit,
      status: 'scheduled'
    }),
    staleTime: DEFAULT_STALE_TIME,
    ...options,
  });
}

