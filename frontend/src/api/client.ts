import type { components } from "../types/api";
import { fixtureApi } from "./fixtureApi";

type Schemas = components["schemas"];
export type Health = Schemas["HealthResponse"];
export type Question = Schemas["Question"];
export type ProfileEntry = Schemas["ProfileEntry"];
export type Profile = Record<string, ProfileEntry>;
export type AnswerResponse = Schemas["AnswerResponse"];
export type CreateSessionResponse = Schemas["CreateSessionResponse"];
export type MessageResponse = Schemas["MessageResponse"];
export type ChecklistItem = Schemas["ChecklistItem"];
export type ChecklistResponse = Schemas["ChecklistResponse"];
export type DocumentAnswer = NonNullable<ChecklistItem["answer"]>;
export type ResultsResponse = Schemas["ResultsResponse"];
export type SchemeResult = Schemas["SchemeResult"];
export type SchemeStatus = SchemeResult["status"];
export type RuleResult = Schemas["RuleResult"];
export type UnlockReport = Schemas["UnlockReport"];
export type PacketResponse = Schemas["PacketResponse"];
export type Scheme = Schemas["Scheme"];
export type ChatResponse = Schemas["ChatResponse"];
export type AnswerValue = AnswerResponse["profile"][string]["value"];

const BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";
const USE_FIXTURES = import.meta.env.VITE_USE_FIXTURES === "true";

export class ApiError extends Error {
  constructor(
    readonly status: number,
    message: string,
  ) {
    super(message);
  }
}

let language = "en";
export function setApiLanguage(lang: string) {
  language = lang;
}

async function request<T>(path: string, body?: unknown): Promise<T> {
  const response = await fetch(`${BASE_URL}/api${path}`, {
    method: body === undefined ? "GET" : "POST",
    headers: { "Accept-Language": language, ...(body === undefined ? {} : { "Content-Type": "application/json" }) },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  if (!response.ok) {
    const detail = await response.json().catch(() => null);
    throw new ApiError(response.status, typeof detail?.detail === "string" ? detail.detail : response.statusText);
  }
  return response.json();
}

const liveApi = {
  health: () => request<Health>("/health"),
  createSession: (lang: string) => request<CreateSessionResponse>("/session", { language: lang }),
  answer: (id: string, field_id: string, value: AnswerValue) =>
    request<AnswerResponse>(`/session/${id}/answer`, { field_id, value }),
  message: (id: string, text: string) => request<MessageResponse>(`/session/${id}/message`, { text }),
  question: (id: string, fieldId: string) => request<Question>(`/session/${id}/question/${fieldId}`),
  checklist: (id: string) => request<ChecklistResponse>(`/session/${id}/documents`),
  saveDocuments: (id: string, answers: Record<string, DocumentAnswer>) =>
    request<{ ok: boolean }>(`/session/${id}/documents`, answers),
  confirm: (id: string) => request<{ confirmed: boolean }>(`/session/${id}/confirm`, {}),
  results: (id: string) => request<ResultsResponse>(`/session/${id}/results`),
  unlock: (id: string) => request<UnlockReport>(`/session/${id}/unlock`),
  packet: (id: string) => request<PacketResponse>(`/session/${id}/packet`),
  scheme: (id: string) => request<Scheme>(`/schemes/${id}`),
  chat: (question: string, lang: string, session_id: string | null) =>
    request<ChatResponse>("/chat", { question, language: lang, session_id }),
};

export type Api = typeof liveApi;
export const api: Api = USE_FIXTURES ? fixtureApi : liveApi;
