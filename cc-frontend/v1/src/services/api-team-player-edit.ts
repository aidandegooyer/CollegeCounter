import { api } from "./api-config";
import type { Team, Player } from "./api";
import { getStorage, ref, uploadBytes, getDownloadURL } from "firebase/storage";

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
  pictureFile: File,
  additionalData?: {
    name?: string;
    school_name?: string;
    elo?: number;
  }
): Promise<{picture_url: string}> => {
  try {
    // Upload to Firebase Storage
    const storage = getStorage();
    const fileExtension = pictureFile.name.split('.').pop() || 'jpg';
    const fileName = `teams/${teamId}_${Date.now()}.${fileExtension}`;
    const storageRef = ref(storage, fileName);
    
    // Upload the file
    await uploadBytes(storageRef, pictureFile);
    
    // Get the download URL
    const downloadURL = await getDownloadURL(storageRef);
    
    // Send the URL and any additional data to the backend
    const updateData = {
      picture: downloadURL,
      ...additionalData
    };
    
    await api.put(`/teams/${teamId}/`, updateData);
    
    return { picture_url: downloadURL };
  } catch (error) {
    console.error('Error uploading team picture:', error);
    throw error;
  }
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
  try {
    // Upload to Firebase Storage
    const storage = getStorage();
    const fileExtension = pictureFile.name.split('.').pop() || 'jpg';
    const fileName = `players/${playerId}_${Date.now()}.${fileExtension}`;
    const storageRef = ref(storage, fileName);
    
    // Upload the file
    await uploadBytes(storageRef, pictureFile);
    
    // Get the download URL
    const downloadURL = await getDownloadURL(storageRef);
    
    // Send the URL and any additional data to the backend
    const updateData = {
      picture: downloadURL,
      ...additionalData
    };
    
    await api.put(`/players/${playerId}/`, updateData);
    
    return { picture_url: downloadURL };
  } catch (error) {
    console.error('Error uploading player picture:', error);
    throw error;
  }
};
