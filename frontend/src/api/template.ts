import { apiFetch } from "../lib/api";
import type {
  TemplateCourseCollection,
  TemplateCreationResponse,
  TemplateDetailResponse,
  ImageUploadResponse,
} from "@/model/template";

import type { TemplatePatchRequest } from "@/model/templateElement";

export const templateApi = {
  getCollection: () => apiFetch<TemplateCourseCollection>("/api/v1/templates"),

  getById: (id: string) =>
    apiFetch<TemplateDetailResponse>(`/api/v1/templates/${id}`),

  upload: (file: File, separator?: string) => {
    const form = new FormData();
    form.append("template", file);
    if (separator) form.append("separator", separator);
    return apiFetch<TemplateCreationResponse>("/api/v1/templates", {
      method: "POST",
      body: form,
    });
  },

  remove: (href: string) => apiFetch(href, { method: "DELETE" }),
  publish: (href: string) => apiFetch<void>(href, { method: "POST" }),

  uploadImage: (href: string, file: File) => {
    const form = new FormData();
    form.append("file", file);
    return apiFetch<ImageUploadResponse>(href, {
      method: "POST",
      body: form,
    });
  },

  publishMany: (href: string, ids: string[]) =>
    apiFetch<void>(href, { method: "POST", body: JSON.stringify({ ids }) }),

  deleteMany: (href: string, ids: string[]) =>
    apiFetch<void>(href, { method: "POST", body: JSON.stringify({ ids }) }),

  update: (href: string, body: TemplateUpdateRequest) =>
    apiFetch<void>(href, { method: "PATCH", body: JSON.stringify(body) }),
};

export const queryKeys = {
  collection: () => ["templates"] as const,
  detail: (id: string) => ["templates", id] as const,
};
