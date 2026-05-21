import { describe, expect, it } from "vitest";
import i18n, { LOCALE_STORAGE_KEY, readStoredLanguage } from ".";

describe("i18n", () => {
  it("defaults first-time visitors to English", () => {
    expect(readStoredLanguage()).toBe("en");
  });

  it("respects a stored Finnish preference", () => {
    window.localStorage.setItem(LOCALE_STORAGE_KEY, "fi");

    expect(readStoredLanguage()).toBe("fi");
  });

  it("falls back to English for unsupported stored values", () => {
    window.localStorage.setItem(LOCALE_STORAGE_KEY, "sv");

    expect(readStoredLanguage()).toBe("en");
  });

  it("persists language changes", async () => {
    await i18n.changeLanguage("fi");

    expect(window.localStorage.getItem(LOCALE_STORAGE_KEY)).toBe("fi");
  });
});
