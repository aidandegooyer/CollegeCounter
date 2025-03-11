interface Player {
    player_id: string;
    nickname: string;
    avatar: string;
    skill_level: number;
    elo: number;
    steam_id?: string;
    faceit_id?: string;
}

interface Team {
    name: string;
    roster?: Player[];
    team_id: string;
    leader: string;
    avatar: string;
    elo: number;
    matches?: Match[];
    playfly_id?: string;
    playfly_participant_id?: string;
    faceit_id?: string;
    school_name?: string;
  }
  
interface Match {
    match_id: string;
    game: string;
    competition: string;
    teams?: {
      team1: Team;
      team2: Team;
    };
    team1_id: string;
    team2_id: string;
    scheduled_time: number;
    status: string;
    match_url: string;
    results_winner?: string;
    results_score_team1?: number;
    results_score_team2?: number;
    platform: string;
    };

interface EloHistory {
    elo: number;
    timestamp: number;
    id: number;
    team_id: string;
    match_id: string;
}

interface RankingItem {
    team_id: string;
    rank: number;
    change: number;
}

interface MatchWeekRanking {
    week: number;
    rankings: RankingItem[];
}


export type { Player, Team, Match, EloHistory, MatchWeekRanking };