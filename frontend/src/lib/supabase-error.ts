/**
 * Maps raw Supabase error messages to translation keys.
 * Returns a translation key if recognized, otherwise returns the fallbackKey.
 */
export function mapSupabaseError(
  message: string,
  keyMap: Record<string, string>,
  fallbackKey: string,
): string {
  const lower = message.toLowerCase();
  for (const [pattern, key] of Object.entries(keyMap)) {
    if (lower.includes(pattern)) return key;
  }
  return fallbackKey;
}

const BACKEND_ERROR_MAP: Record<string, string> = {
  "please keep your input appropriate": "errorProfanity",
  "please describe your idea in at least a few words": "errorMinLength",
  "doesn't look like a real idea": "errorGibberish",
  "insufficient credits": "outOfCredits",
  "temporarily unavailable": "serviceUnavailable",
  "processing failed": "processingFailed",
  "processing timed out": "processingTimedOut",
  "too large": "audioTooLarge",
  "transcription failed": "transcriptionFailed",
};

/**
 * Maps raw backend API error messages to translation keys.
 * Returns a translation key if recognized, otherwise returns the fallbackKey.
 */
export function mapBackendError(
  message: string,
  fallbackKey: string,
): string {
  const lower = message.toLowerCase();
  for (const [pattern, key] of Object.entries(BACKEND_ERROR_MAP)) {
    if (lower.includes(pattern)) return key;
  }
  return fallbackKey;
}
