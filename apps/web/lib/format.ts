import type { Business } from "@/types/business";

export function businessLocation(business: Business): string {
  if (business.address.formatted) {
    return business.address.formatted;
  }

  return [business.address.city, business.address.country].filter(Boolean).join(", ") || "Not listed";
}

export function safeWebsiteUrl(value: string | null): string | null {
  if (!value) {
    return null;
  }

  try {
    const hasProtocol = /^[a-z][a-z\d+.-]*:/i.test(value);
    const url = new URL(hasProtocol ? value : `https://${value}`);
    return url.protocol === "http:" || url.protocol === "https:" ? url.toString() : null;
  } catch {
    return null;
  }
}

export function displayWebsite(value: string): string {
  try {
    const url = new URL(safeWebsiteUrl(value) ?? value);
    return url.hostname.replace(/^www\./, "");
  } catch {
    return value;
  }
}

