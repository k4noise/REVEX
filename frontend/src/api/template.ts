import { apiFetch } from "../lib/api";
import type {
  TemplateCourseCollection,
  TemplateCreationResponse,
  TemplateDetailResponse,
  TemplateUpdateRequest,
  ImageUploadResponse,
} from "../model/template";
import type {
  ReportCreationResponse,
  AllReportsResponse,
} from "../model/report";

export const templateApi = {
  getCollection: () => apiFetch<TemplateCourseCollection>("/templates"),

  getById: (id: string) => apiFetch<TemplateDetailResponse>(`/templates/${id}`),

  upload: (file: File, separator?: string) => {
    const form = new FormData();
    form.append("template", file);
    if (separator !== undefined) {
      form.append("separator", separator);
    }
    return apiFetch<TemplateCreationResponse>("/templates", {
      method: "POST",
      body: form,
    });
  },

  remove: (href: string) => apiFetch<void>(href, { method: "DELETE" }),

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
    apiFetch<void>(href, {
      method: "POST",
      body: JSON.stringify({ ids }),
    }),

  deleteMany: (href: string, ids: string[]) =>
    apiFetch<void>(href, {
      method: "POST",
      body: JSON.stringify({ ids }),
    }),

  update: (href: string, body: TemplateUpdateRequest) =>
    apiFetch<void>(href, {
      method: "PATCH",
      body: JSON.stringify(body),
    }),

  getReports: (href: string) => apiFetch<AllReportsResponse>(href),

  createReport: (href: string) =>
    apiFetch<ReportCreationResponse>(href, { method: "POST" }),
};

export const queryKeys = {
  all: ["templates"] as const,
  collection: () => ["templates", "list"] as const,
  detail: (id: string) => ["templates", id] as const,
  reports: (id: string) => ["templates", id, "reports"] as const,
};
