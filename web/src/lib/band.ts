// Approximate IELTS band from a percent-correct on a short practice/mock set.
// This is a coarse estimate (sets are far shorter than a real 40-question paper),
// labelled as such in the UI — not an official raw→band conversion.
export function bandFromPct(pct: number): number {
  if (pct >= 90) return 8;
  if (pct >= 80) return 7.5;
  if (pct >= 70) return 7;
  if (pct >= 60) return 6.5;
  if (pct >= 50) return 6;
  if (pct >= 40) return 5.5;
  if (pct >= 30) return 5;
  return 4.5;
}

/** Round a number to the nearest 0.5 (IELTS overall convention). */
export function roundHalf(x: number): number {
  return Math.round(x * 2) / 2;
}
