import { createContext, useContext, useMemo, useState, type ReactNode } from "react";

const STORAGE_KEY = "citizenassist.session";

function readStored(): string | null {
  try {
    return sessionStorage.getItem(STORAGE_KEY);
  } catch {
    return null;
  }
}

interface SessionState {
  sessionId: string | null;
  setSessionId: (id: string | null) => void;
}

const SessionContext = createContext<SessionState | null>(null);

export function SessionProvider({ children }: { children: ReactNode }) {
  const [sessionId, setId] = useState<string | null>(readStored);

  const value = useMemo<SessionState>(
    () => ({
      sessionId,
      setSessionId: (id) => {
        setId(id);
        try {
          if (id) sessionStorage.setItem(STORAGE_KEY, id);
          else sessionStorage.removeItem(STORAGE_KEY);
        } catch {
          // The session simply lasts until the page reloads.
        }
      },
    }),
    [sessionId],
  );

  return <SessionContext.Provider value={value}>{children}</SessionContext.Provider>;
}

export function useSession(): SessionState {
  const session = useContext(SessionContext);
  if (!session) throw new Error("useSession must be used inside SessionProvider");
  return session;
}
