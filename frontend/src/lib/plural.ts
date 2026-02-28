/**
 * Lithuanian plural category based on CLDR rules.
 * https://www.unicode.org/cldr/charts/48/supplemental/language_plural_rules.html
 *
 * one:   n % 10 = 1 and n % 100 ∉ 11..19  → 1, 21, 31, 101 …
 * few:   n % 10 = 2..9 and n % 100 ∉ 11..19 → 2–9, 22–29, 32 …
 * other: n % 10 = 0 or n % 100 = 11..19   → 0, 10–20, 30, 100 …
 */
export function ltPlural(n: number): "one" | "few" | "other" {
  const mod10 = n % 10;
  const mod100 = n % 100;

  if (mod10 === 1 && (mod100 < 11 || mod100 > 19)) return "one";
  if (mod10 >= 2 && mod10 <= 9 && (mod100 < 11 || mod100 > 19)) return "few";
  return "other";
}
