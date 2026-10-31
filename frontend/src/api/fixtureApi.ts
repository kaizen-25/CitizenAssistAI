import type { Api } from "./client";
import checklist from "../fixtures/checklist.json";
import chat from "../fixtures/chat.json";
import flow from "../fixtures/flow.json";
import health from "../fixtures/health.json";
import message from "../fixtures/message.json";
import packet from "../fixtures/packet.json";
import questions from "../fixtures/questions.json";
import results from "../fixtures/results.json";
import schemes from "../fixtures/schemes.json";
import session from "../fixtures/session.json";
import unlock from "../fixtures/unlock.json";

let step = 0;

export const fixtureApi = {
  health: async () => health,
  createSession: async () => {
    step = 0;
    return session;
  },
  answer: async () => flow[Math.min(step++, flow.length - 1)],
  message: async () => message,
  question: async (_id: string, fieldId: string) => questions[fieldId as keyof typeof questions],
  checklist: async () => checklist,
  saveDocuments: async () => ({ ok: true }),
  confirm: async () => ({ confirmed: true }),
  results: async () => results,
  unlock: async () => unlock,
  packet: async () => packet,
  scheme: async (id: string) => schemes[id as keyof typeof schemes],
  chat: async () => chat,
} as unknown as Api;
