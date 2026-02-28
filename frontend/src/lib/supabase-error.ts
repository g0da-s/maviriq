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
