import { getRequestConfig } from "next-intl/server";
import { cookies, headers } from "next/headers";

const SUPPORTED_LOCALES = ["en", "lt"] as const;
type Locale = (typeof SUPPORTED_LOCALES)[number];

function detectLocale(acceptLanguage: string | null): Locale {
  if (!acceptLanguage) return "en";
  const preferred = acceptLanguage.toLowerCase();
  if (preferred.startsWith("lt") || preferred.includes(",lt")) return "lt";
  return "en";
}

export default getRequestConfig(async () => {
  const cookieStore = await cookies();
  const cookieLocale = cookieStore.get("locale")?.value;

  let locale: Locale;
  if (cookieLocale && SUPPORTED_LOCALES.includes(cookieLocale as Locale)) {
    locale = cookieLocale as Locale;
  } else {
    const headerStore = await headers();
    locale = detectLocale(headerStore.get("accept-language"));
  }

  return {
    locale,
    messages: (await import(`../../messages/${locale}.json`)).default,
  };
});
