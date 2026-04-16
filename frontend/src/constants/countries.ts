export const COUNTRIES: { code: string; label: string }[] = [
  { code: "AT", label: "Austria" },
  { code: "AU", label: "Australia" },
  { code: "BE", label: "Belgium" },
  { code: "BR", label: "Brazil" },
  { code: "CA", label: "Canada" },
  { code: "CH", label: "Switzerland" },
  { code: "DE", label: "Germany" },
  { code: "DK", label: "Denmark" },
  { code: "ES", label: "Spain" },
  { code: "FR", label: "France" },
  { code: "GB", label: "Great Britain" },
  { code: "IT", label: "Italy" },
  { code: "NL", label: "Netherlands" },
  { code: "PL", label: "Poland" },
  { code: "US", label: "United States" },
];

export const COUNTRY_CODES = COUNTRIES.map((c) => c.code);

export function countryLabel(code: string): string {
  return COUNTRIES.find((c) => c.code === code)?.label ?? code;
}
