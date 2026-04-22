export type RuntimeConfig = {
  apiBaseUrl: string;
  cognitoClientId: string;
  cognitoHostedUiBaseUrl: string;
};

function getRequiredEnv(name: keyof ImportMetaEnv) {
  const value = import.meta.env[name]?.trim();
  if (!value) {
    throw new Error(`Missing required frontend env var: ${name}.`);
  }
  return value;
}

export function getRuntimeConfig(): RuntimeConfig {
  return {
    apiBaseUrl: getRequiredEnv("VITE_API_BASE_URL"),
    cognitoClientId: getRequiredEnv("VITE_COGNITO_CLIENT_ID"),
    cognitoHostedUiBaseUrl: getRequiredEnv("VITE_COGNITO_HOSTED_UI_BASE_URL"),
  };
}
