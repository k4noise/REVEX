import { apiFetch } from "../lib/api";
import type {
  FullWorkResponse,
  UpdateAnswerDataPayload,
  UpdateAnswerScorePayload,
  HintRequest,
  HintResponse,
} from "../model/report";

export const reportApi = {
  getById: (id: string, signal?: AbortSignal) =>
    apiFetch<FullWorkResponse>(`/reports/${id}`, { signal }),

  saveAnswers: (href: string, answers: UpdateAnswerDataPayload[]) =>
    apiFetch<void>(href, {
      method: "PATCH",
      body: JSON.stringify(answers),
    }),

  submit: (href: string) => apiFetch<void>(href, { method: "POST" }),

  unsubmit: (href: string) => apiFetch<void>(href, { method: "DELETE" }),

  grade: (href: string, answers: UpdateAnswerScorePayload[]) =>
    apiFetch<void>(href, {
      method: "PATCH",
      body: JSON.stringify(answers),
    }),

  getHint: (href: string, request: HintRequest, signal?: AbortSignal) =>
    apiFetch<HintResponse | null>(href, {
      method: "POST",
      body: JSON.stringify(request),
      signal,
    }),
};

export const reportQueryKeys = {
  all: ["reports"] as const,
  detail: (id: string) => ["reports", id] as const,
};
