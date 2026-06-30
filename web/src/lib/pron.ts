// Approximate word-match accuracy between a read-aloud target and what the
// browser speech recogniser heard. Coarse (word presence, not phonemes).

function tokens(s: string): string[] {
  return s
    .toLowerCase()
    .replace(/[^a-z0-9\s']/g, " ")
    .split(/\s+/)
    .filter(Boolean);
}

export interface Accuracy {
  accuracy: number; // 0–100, matched target words / total target words
  missed: string[]; // target words not found in the transcript
}

export function wordAccuracy(target: string, transcript: string): Accuracy {
  const want = tokens(target);
  if (want.length === 0) return { accuracy: 0, missed: [] };
  const heard = new Set(tokens(transcript));
  const missed = want.filter((w) => !heard.has(w));
  const matched = want.length - missed.length;
  return { accuracy: Math.round((matched / want.length) * 100), missed };
}
