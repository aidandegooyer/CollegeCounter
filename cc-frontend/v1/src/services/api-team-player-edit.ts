import { api } from "./api-config";
import type { Team, Player } from "./api";

// Team update and image upload functions
export const updateTeam = async (
  teamId: string,
  data: {
    name?: string;
    school_name?: string;
    elo?: number;
  }
): Promise<Team> => {
  const response = await api.put(`/teams/${teamId}/`, data);
  return response.data.team;
};

export const uploadTeamPicture = async (
  teamId: string,
  pictureFile: File
): Promise<{picture_url: string}> => {
  const formData = new FormData();
  formData.append('picture', pictureFile);
  
  const response = await api.post(`/teams/${teamId}/picture/`, formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
  });
  return response.data;
};

// Player update and image upload functions
export const updatePlayer = async (
  playerId: string,
  data: {
    name?: string;
    steam_id?: string;
    faceit_id?: string;
    elo?: number;
    skill_level?: number;
    team_id?: string | null;
    benched?: boolean;
    visible?: boolean;
  }
): Promise<Player> => {
  const response = await api.put(`/players/${playerId}/`, data);
  return response.data.player;
};

export const uploadPlayerPicture = async (
  playerId: string,
  pictureFile: File
): Promise<{picture_url: string}> => {
  const formData = new FormData();
  formData.append('picture', pictureFile);
  
  const response = await api.post(`/players/${playerId}/picture/`, formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
  });
  return response.data;
};
