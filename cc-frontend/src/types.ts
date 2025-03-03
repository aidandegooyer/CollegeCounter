interface Player {
    player_id: string;
    nickname: string;
    avatar: string;
    skill_level: number;
    elo: number;
}

interface Team {
    name: string;
    roster?: Player[];
    team_id: string;
    leader: string;
    avatar: string;
    elo: number;
    matches?: Match[];
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
    };


export type { Player, Team, Match };