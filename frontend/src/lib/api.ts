export class ApiError extends Error {
  status: number;
  body: unknown;

  constructor(status: number, message: string, body?: unknown) {
    super(message);
    this.status = status;
    this.body = body;
  }
}

const API_PREFIX = "/api/";
const API_BASE = `${API_PREFIX}v1`;

let refreshPromise: Promise<void> | null = null;

type ErrorBody = {
  error_type?: string;
  detail?: string;
  [key: string]: unknown;
};

function resolveUrl(url: string): string {
  if (url.startsWith("http://") || url.startsWith("https://")) {
    return url;
  }
  if (url.startsWith(API_PREFIX)) {
    return url;
  }
  if (url.startsWith("/")) {
    return `${API_BASE}${url}`;
  }
  return `${API_BASE}/${url}`;
}

async function refreshToken(signal?: AbortSignal): Promise<void> {
  const res = await fetch(resolveUrl("/lti/jwt-refresh"), {
    method: "POST",
    credentials: "include",
    signal,
  });

  if (!res.ok) {
    throw new ApiError(res.status, "Refresh failed");
  }
}

export function isJwtError(body: unknown): body is ErrorBody {
  return (
    typeof body === "object" &&
    body !== null &&
    "error_type" in body &&
    (body as ErrorBody).error_type === "JWTDecodeError"
  );
}

export async function apiFetch<T>(
  url: string,
  options: RequestInit = {},
  retry = true,
): Promise<T> {
  const targetUrl = resolveUrl(url);
  const isFormData = options.body instanceof FormData;

  const res = await fetch(targetUrl, {
    ...options,
    credentials: "include",
    headers: isFormData
      ? options.headers
      : {
          "Content-Type": "application/json",
          ...options.headers,
        },
  });

  const body: unknown =
    res.status !== 204 ? await res.json().catch(() => null) : null;

  if (!res.ok) {
    if (res.status === 401 && isJwtError(body) && retry) {
      if (!refreshPromise) {
        refreshPromise = refreshToken(options.signal ?? undefined)
          .catch(() => {})
          .finally(() => {
            refreshPromise = null;
          });
      }
      await refreshPromise;
      return apiFetch<T>(url, options, false);
    }

    const message =
      (typeof body === "object" &&
        body !== null &&
        "detail" in body &&
        typeof (body as ErrorBody).detail === "string" &&
        (body as ErrorBody).detail) ||
      res.statusText ||
      "Request failed";

    throw new ApiError(res.status, message, body);
  }

  if (res.status === 204) {
    return undefined as T;
  }

  return body as T;
}

export function isApiError(error: unknown): error is ApiError {
  return error instanceof ApiError;
}

export function isUnauthorized(error: unknown): boolean {
  return isApiError(error) && error.status === 401;
}

export function isForbidden(error: unknown): boolean {
  return isApiError(error) && error.status === 403;
}
