import { describe, expect, it } from "vitest";
import { generateCodeChallenge, generateCodeVerifier } from "./pkce";

describe("pkce utilities", () => {
  it("generates the expected RFC 7636 code challenge", async () => {
    const challenge = await generateCodeChallenge(
      "dBjftJeZ4CVP-mB92K27uhbUJU1p1r_wW1gFWFOEjXk"
    );

    expect(challenge).toBe("E9Melhoa2OwvFrEMTJguCHaoeK1t8URWbuGJSstw-cM");
  });

  it("creates a URL-safe code verifier", () => {
    const verifier = generateCodeVerifier();

    expect(verifier).toMatch(/^[A-Za-z0-9\-_]+$/);
    expect(verifier.length).toBeGreaterThanOrEqual(43);
  });
});
