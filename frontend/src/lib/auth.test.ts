import { describe, expect, it } from "vitest";
import { buildHostedUiAuthorizeUrl } from "./auth";

describe("Hosted UI auth", () => {
  it("requests profile scope so ID tokens include readable custom attributes", () => {
    const redirectUrl = new URL(
      buildHostedUiAuthorizeUrl(
        {
          apiBaseUrl: "https://api.example.com/dev",
          cognitoClientId: "client-id",
          cognitoHostedUiBaseUrl: "https://leaseflow.auth.eu-north-1.amazoncognito.com",
        },
        "code-challenge",
        "oauth-state"
      )
    );

    expect(redirectUrl.pathname).toBe("/oauth2/authorize");
    expect(redirectUrl.searchParams.get("scope")).toBe("openid email profile");
  });
});
