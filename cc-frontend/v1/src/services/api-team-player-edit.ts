import { api } from "./api-config";
import type { Team, Player } from "./api";

// Team creation from Faceit
export interface ImportTeamFromFaceitRequest {
  team_url?: string;
  team_id?: string;
}

export interface ImportTeamFromFaceitResponse {
  message: string;
  team: {
    id: string;
    name: string;
    picture: string;
    elo: number;
  };
  players: Array<{
    id: string;
    name: string;
    existed: boolean;
  }>;
  faceit_team_id: string;
}

export const importTeamFromFaceit = async (
  data: ImportTeamFromFaceitRequest
): Promise<ImportTeamFromFaceitResponse> => {
  const response = await api.post(`/teams/import-faceit/`, data);
  return response.data;
};

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

// The backend resizes the picture, stores it on the image CDN and saves its
// URL on the team/player/event (cc-backend/v1/cc/images.py)
const uploadPicture = async (path: string, pictureFile: File): Promise<string> => {
  const form = new FormData();
  form.append("picture", pictureFile);
  const response = await api.post(path, form);
  return response.data.picture_url;
};

export const uploadTeamPicture = async (
  teamId: string,
  pictureFile: File,
  additionalData?: {
    name?: string;
    school_name?: string;
    elo?: number;
  }
): Promise<{picture_url: string}> => {
  // Picture first, so a rejected picture doesn't leave the rest half-saved
  const picture_url = await uploadPicture(`/teams/${teamId}/picture/`, pictureFile);
  if (additionalData) {
    await api.put(`/teams/${teamId}/`, additionalData);
  }
  return { picture_url };
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
  pictureFile: File,
  additionalData?: {
    name?: string;
    steam_id?: string;
    faceit_id?: string;
    elo?: number;
    skill_level?: number;
    team_id?: string | null;
    benched?: boolean;
    visible?: boolean;
  }
): Promise<{picture_url: string}> => {
  const picture_url = await uploadPicture(`/players/${playerId}/picture/`, pictureFile);
  if (additionalData) {
    await api.put(`/players/${playerId}/`, additionalData);
  }
  return { picture_url };
};

export const uploadEventPicture = async (
  customEventId: string,
  pictureFile: File
): Promise<{picture_url: string}> => {
  const picture_url = await uploadPicture(
    `/custom-events/${customEventId}/picture/`,
    pictureFile
  );
  return { picture_url };
};
