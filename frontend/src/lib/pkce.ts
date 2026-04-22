function base64UrlEncode(input: Uint8Array) {
  const stringValue = String.fromCharCode(...input);
  return btoa(stringValue).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/g, "");
}

export function generateRandomString(bytes = 32) {
  const values = new Uint8Array(bytes);
  crypto.getRandomValues(values);
  return base64UrlEncode(values);
}

export function generateCodeVerifier() {
  return generateRandomString(48);
}

export async function generateCodeChallenge(verifier: string) {
  const digest = await crypto.subtle.digest(
    "SHA-256",
    new TextEncoder().encode(verifier)
  );
  return base64UrlEncode(new Uint8Array(digest));
}
