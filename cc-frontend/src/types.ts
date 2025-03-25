interface Player {
    player_id: string;
    nickname: string;
    avatar: string;
    skill_level: number;
    elo: number;
    steam_id?: string;
    faceit_id?: string;
    visible?: boolean;
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

interface Event {
    event_id: string;
    title: string;
    description: string;
    start_date: number;
    end_date: number;
    winner: Team;
    bracket: EventMatch[];
}

interface EventMatch {
    id: string;
    match_id?: string;
    match: Match;
    round: number;
    number_in_bracket: number;
    event_id: string;
    isbye: boolean;
    bye_team_id: string;
}



export type { Player, Team, Match, EloHistory, MatchWeekRanking, Event, EventMatch, };