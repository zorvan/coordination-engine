/**
 * Fairness Ledger Domain Service
 * 
 * Computes fairness metrics for matches to ensure:
 * - Prevents one enthusiastic minority dominating
 * - Ensures majority mild dissatisfaction isn't ignored
 * - Provides metrics for transparency in ranking
 * 
 * Design decisions:
 * - Regret points: No=2, Prefer Not=1, Yes=0, Strong Yes=0
 * - Enthusiasm bonus: Strong Yes=2, Yes=1
 * - Fairness score normalized 0-1
 */

const computeRegret = function(votes) {
  let totalRegret = 0;
  
  for (const vote of votes) {
    switch (vote) {
      case 'No':
        totalRegret += 2;
        break;
      case 'Prefer Not':
        totalRegret += 1;
        break;
      case 'Yes':
        totalRegret += 0;
        break;
      case 'Strong Yes':
        totalRegret += 0;
        break;
      default:
        // Unknown vote type - treat as No
        totalRegret += 2;
    }
  }
  
  return totalRegret;
};

const computeEnthusiasm = function(votes) {
  let enthusiasmScore = 0;
  
  for (const vote of votes) {
    switch (vote) {
      case 'Yes':
        enthusiasmScore += 1;
        break;
      case 'Strong Yes':
        enthusiasmScore += 2;
        break;
      default:
        // No or Prefer Not - no enthusiasm
        enthusiasmScore += 0;
    }
  }
  
  return enthusiasmScore;
};

const computeParticipationRate = function(totalMembers, votingMembers) {
  if (totalMembers === 0) return 0;
  return votingMembers / totalMembers;
};

const computeFairnessScore = function(regret, enthusiasm, participationRate) {
  // Normalize regret (max possible regret = 2 * totalMembers)
  // Normalize enthusiasm (max possible = 2 * totalMembers)
  // Combined with participation rate for fairness score
  
  // Normalized regret (0-1, lower is better)
  const normalizedRegret = Math.min(regret / 2, 1);
  
  // Normalized enthusiasm (0-1, higher is better)
  const normalizedEnthusiasm = enthusiasm / 2;
  
  // Combined score: lower regret + higher enthusiasm + better participation
  const combinedScore = 
    (1 - normalizedRegret) * 0.5 +
    normalizedEnthusiasm * 0.3 +
    participationRate * 0.2;
  
  return Math.round(combinedScore * 100) / 100;
};

export { computeRegret,
  computeEnthusiasm,
  computeParticipationRate,
  computeFairnessScore, };