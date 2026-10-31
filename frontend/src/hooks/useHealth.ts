import { useEffect, useState } from "react";
import { getHealth, type Health } from "../api/client";

export function useHealth(): { health: Health | null; failed: boolean } {
  const [health, setHealth] = useState<Health | null>(null);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    getHealth().then(setHealth).catch(() => setFailed(true));
  }, []);

  return { health, failed };
}
