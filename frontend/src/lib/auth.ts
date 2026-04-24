import type { RuntimeConfig } from "./config";
import { generateCodeChallenge, generateCodeVerifier, generateRandomString } from "./pkce";

const AUTH_SESSION_KEY = "leaseflow.frontend.authSession";
const CODE_VERIFIER_KEY = "leaseflow.frontend.codeVerifier";
const OAUTH_STATE_KEY = "leaseflow.frontend.oauthState";
const RETURN_PATH_KEY = "leaseflow.frontend.returnPath";
const EXPIRY_SKEW_MS = 10_000;

export type StoredAuthSession = {
  accessToken: string;
  expiresAt: number;
  idToken: string;
  refreshToken?: string;
  tokenType: string;
};

type TokenResponse = {
  access_token: string;
  expires_in: number;
  id_token: string;
  refresh_token?: string;
  token_type: string;
};

type CompletedSignIn = {
  returnPath: string;
  session: StoredAuthSession;
};

function normalizeBaseUrl(url: string) {
  return url.replace(/\/+$/g, "");
}

function getRedirectUri() {
  return new URL("/auth/callback", window.location.origin).toString();
}

function getLogoutUri() {
  return new URL("/", window.location.origin).toString();
}

function storePendingSignIn(codeVerifier: string, oauthState: string, returnPath: string) {
  sessionStorage.setItem(CODE_VERIFIER_KEY, codeVerifier);
  sessionStorage.setItem(OAUTH_STATE_KEY, oauthState);
  sessionStorage.setItem(RETURN_PATH_KEY, returnPath);
}

function clearPendingSignIn() {
  sessionStorage.removeItem(CODE_VERIFIER_KEY);
  sessionStorage.removeItem(OAUTH_STATE_KEY);
  sessionStorage.removeItem(RETURN_PATH_KEY);
}

function getPendingValue(key: string) {
  return sessionStorage.getItem(key);
}

function saveAuthSession(session: StoredAuthSession) {
  sessionStorage.setItem(AUTH_SESSION_KEY, JSON.stringify(session));
}

export function clearAuthSession() {
  clearPendingSignIn();
  sessionStorage.removeItem(AUTH_SESSION_KEY);
}

function buildStoredSession(tokenResponse: TokenResponse): StoredAuthSession {
  return {
    accessToken: tokenResponse.access_token,
    expiresAt: Date.now() + tokenResponse.expires_in * 1000 - EXPIRY_SKEW_MS,
    idToken: tokenResponse.id_token,
    refreshToken: tokenResponse.refresh_token,
    tokenType: tokenResponse.token_type,
  };
}

function parseStoredSession(value: string | null) {
  if (!value) {
    return null;
  }

  try {
    const parsed = JSON.parse(value) as StoredAuthSession;
    if (!parsed.idToken || !parsed.accessToken || !parsed.expiresAt) {
      clearAuthSession();
      return null;
    }
    if (parsed.expiresAt <= Date.now()) {
      clearAuthSession();
      return null;
    }
    return parsed;
  } catch {
    clearAuthSession();
    return null;
  }
}

async function exchangeAuthorizationCode(
  config: RuntimeConfig,
  code: string,
  codeVerifier: string
) {
  const response = await fetch(
    `${normalizeBaseUrl(config.cognitoHostedUiBaseUrl)}/oauth2/token`,
    {
      method: "POST",
      headers: {
        "Content-Type": "application/x-www-form-urlencoded",
      },
      body: new URLSearchParams({
        client_id: config.cognitoClientId,
        code,
        code_verifier: codeVerifier,
        grant_type: "authorization_code",
        redirect_uri: getRedirectUri(),
      }),
    }
  );

  const body = (await response.json().catch(() => null)) as
    | (TokenResponse & { error?: string; error_description?: string })
    | null;

  if (!response.ok || !body) {
    throw new Error(body?.error_description || body?.error || "Sign-in failed during token exchange.");
  }

  return body;
}

export async function redirectToHostedUiSignIn(
  config: RuntimeConfig,
  returnPath: string
) {
  const verifier = generateCodeVerifier();
  const challenge = await generateCodeChallenge(verifier);
  const oauthState = generateRandomString(24);

  storePendingSignIn(verifier, oauthState, returnPath);

  window.location.assign(buildHostedUiAuthorizeUrl(config, challenge, oauthState));
}

export function buildHostedUiAuthorizeUrl(
  config: RuntimeConfig,
  challenge: string,
  oauthState: string
) {
  const authorizeUrl = new URL(
    `${normalizeBaseUrl(config.cognitoHostedUiBaseUrl)}/oauth2/authorize`
  );

  authorizeUrl.searchParams.set("client_id", config.cognitoClientId);
  authorizeUrl.searchParams.set("redirect_uri", getRedirectUri());
  authorizeUrl.searchParams.set("response_type", "code");
  authorizeUrl.searchParams.set("scope", "openid email profile");
  authorizeUrl.searchParams.set("code_challenge_method", "S256");
  authorizeUrl.searchParams.set("code_challenge", challenge);
  authorizeUrl.searchParams.set("state", oauthState);

  return authorizeUrl.toString();
}

export function redirectToHostedUiSignOut(config: RuntimeConfig) {
  const logoutUrl = new URL(`${normalizeBaseUrl(config.cognitoHostedUiBaseUrl)}/logout`);
  logoutUrl.searchParams.set("client_id", config.cognitoClientId);
  logoutUrl.searchParams.set("logout_uri", getLogoutUri());
  window.location.assign(logoutUrl.toString());
}

export async function completeHostedUiSignIn(
  config: RuntimeConfig,
  currentUrl = window.location.href
): Promise<CompletedSignIn> {
  const url = new URL(currentUrl);
  const oauthError = url.searchParams.get("error");
  if (oauthError) {
    throw new Error(url.searchParams.get("error_description") || oauthError);
  }

  const code = url.searchParams.get("code");
  const returnedState = url.searchParams.get("state");
  const expectedState = getPendingValue(OAUTH_STATE_KEY);
  const codeVerifier = getPendingValue(CODE_VERIFIER_KEY);

  if (!code || !returnedState) {
    throw new Error("Authorization callback is missing code or state.");
  }

  if (!expectedState || returnedState !== expectedState) {
    clearPendingSignIn();
    throw new Error("Authorization state did not match the browser session.");
  }

  if (!codeVerifier) {
    clearPendingSignIn();
    throw new Error("PKCE verifier is missing from the browser session.");
  }

  const tokenResponse = await exchangeAuthorizationCode(config, code, codeVerifier);
  const session = buildStoredSession(tokenResponse);
  saveAuthSession(session);

  const returnPath = getPendingValue(RETURN_PATH_KEY) || "/properties";
  clearPendingSignIn();

  return { returnPath, session };
}

export function loadStoredSession() {
  return parseStoredSession(sessionStorage.getItem(AUTH_SESSION_KEY));
}
