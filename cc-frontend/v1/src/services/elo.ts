/**
 * Calculate the number of "stars" for a match based on team ELO ratings
 * 
 * @param team1Elo - ELO rating of team 1
 * @param team2Elo - ELO rating of team 2
 * @returns Number of stars (1-5) representing match quality/excitement
 */
export function calculateMatchStars(team1Elo: number, team2Elo: number): number {
  // ===========================================
  // TWEAKABLE PARAMETERS
  // ===========================================

  // COMPETITIVENESS TUNING
  const COMPETITIVENESS_DECAY_RATE = 400;     // Lower = punishes ELO differences more harshly
  // 200 = very harsh, 400 = moderate, 600 = lenient

  // TEAM QUALITY TUNING  
  const QUALITY_MIDPOINT_ELO = 1800;          // ELO where quality score = 0.5 (average)
  // Lower = easier to get high quality scores

  const QUALITY_CURVE_STEEPNESS = 400;        // How quickly quality score changes around midpoint
  // Lower = steeper curve, higher = gentler curve

  // STAR RATING THRESHOLDS (for multiplicative score: competitiveness × quality)
  const FIVE_STAR_THRESHOLD = 0.6;            // Minimum score for 5 stars (elite competitive matches)
  const FOUR_STAR_THRESHOLD = 0.5;            // Minimum score for 4 stars (great matches)
  const THREE_STAR_THRESHOLD = 0.35;           // Minimum score for 3 stars (good matches)
  const TWO_STAR_THRESHOLD = 0.18;            // Minimum score for 2 stars (decent matches)
  // Below this = 1 star (poor matches)

  // ===========================================
  // CALCULATIONS (Don't modify below this line)
  // ===========================================

  // Calculate average ELO (overall quality of teams)
  const avgElo = (team1Elo + team2Elo) / 2;

  // Calculate ELO difference (how close the match is)
  const eloDiff = Math.abs(team1Elo - team2Elo);

  // Calculate competitiveness score (0-1, where 1 is perfectly matched)
  // Use exponential decay to punish large differences
  const competitivenessScore = Math.exp(-eloDiff / COMPETITIVENESS_DECAY_RATE) + .15;

  // Calculate team quality score (0-1, where 1 is elite teams)
  // Use sigmoid function to normalize ELO to 0-1 range
  const qualityScore = 1 / (1 + Math.exp(-(avgElo - QUALITY_MIDPOINT_ELO) / QUALITY_CURVE_STEEPNESS));

  // Calculate final game score using multiplication
  // This naturally penalizes low scores in either dimension
  const gameScore = competitivenessScore * qualityScore;

  // Clamp gameScore if avgElo is less than 2000
  const clampedGameScore = avgElo < 2000 ? Math.min(gameScore, 0.49) : gameScore;

  // Map game score to 1-5 stars
  if (clampedGameScore >= FIVE_STAR_THRESHOLD) return 5;      // Exceptional matches
  if (clampedGameScore >= FOUR_STAR_THRESHOLD) return 4;      // Great matches  
  if (clampedGameScore >= THREE_STAR_THRESHOLD) return 3;     // Good matches
  if (clampedGameScore >= TWO_STAR_THRESHOLD) return 2;       // Decent matches
  return 1;                                             // Poor matches
}

/**
 * Calculate win probability for team1 vs team2 based on ELO difference
 * Uses standard ELO formula
 * 
 * @param team1Elo - ELO rating of team 1
 * @param team2Elo - ELO rating of team 2
 * @returns Win probability for team1 (0-1)
 */
export function calculateWinProbability(team1Elo: number, team2Elo: number): number {
  const eloDiff = team1Elo - team2Elo;
  return 1 / (1 + Math.pow(10, -eloDiff / 400));
}

