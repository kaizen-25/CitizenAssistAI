import healthFixture from "../fixtures/health.json";
import type { components } from "../types/api";

export type Health = components["schemas"]["HealthResponse"];

const BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";
const USE_FIXTURES = import.meta.env.VITE_USE_FIXTURES === "true";

export async function getHealth(): Promise<Health> {
  if (USE_FIXTURES) return healthFixture;
  const response = await fetch(`${BASE_URL}/api/health`);
  if (!response.ok) throw new Error(`GET /api/health failed with ${response.status}`);
  return response.json();
}
