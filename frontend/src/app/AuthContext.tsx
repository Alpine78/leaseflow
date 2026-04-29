import {
  createContext,
  useContext,
  useMemo,
  useState,
  type PropsWithChildren,
} from "react";
import { getRuntimeConfig } from "../lib/config";
import {
  clearAuthSession,
  completeHostedUiSignIn,
  loadStoredSession,
  redirectToHostedUiSignIn,
  redirectToHostedUiSignOut,
  type StoredAuthSession,
} from "../lib/auth";

export type AuthContextValue = {
  session: StoredAuthSession | null;
  isAuthenticated: boolean;
  completeSignIn: (currentUrl?: string) => Promise<string>;
  markSessionExpired: () => void;
  signIn: (returnPath?: string) => Promise<void>;
  signOut: () => void;
};

export const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: PropsWithChildren) {
  const [session, setSession] = useState<StoredAuthSession | null>(() => loadStoredSession());

  const value = useMemo<AuthContextValue>(
    () => ({
      session,
      isAuthenticated: session !== null,
      async completeSignIn(currentUrl) {
        const result = await completeHostedUiSignIn(getRuntimeConfig(), currentUrl);
        setSession(result.session);
        return result.returnPath;
      },
      markSessionExpired() {
        clearAuthSession();
        setSession(null);
      },
      async signIn(returnPath = "/dashboard") {
        await redirectToHostedUiSignIn(getRuntimeConfig(), returnPath);
      },
      signOut() {
        clearAuthSession();
        setSession(null);
        redirectToHostedUiSignOut(getRuntimeConfig());
      },
    }),
    [session]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const value = useContext(AuthContext);
  if (!value) {
    throw new Error("useAuth must be used within AuthProvider.");
  }
  return value;
}
