import "@testing-library/jest-dom/vitest";
import { afterEach } from "vitest";
import i18n, { LOCALE_STORAGE_KEY } from "../i18n";

afterEach(async () => {
  window.localStorage.removeItem(LOCALE_STORAGE_KEY);
  await i18n.changeLanguage("en");
});
