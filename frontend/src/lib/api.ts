export class ApiError extends Error {
  status: number;
  body: unknown;

  constructor(status: number, message: string, body?: unknown) {
    super(message);
    this.status = status;
    this.body = body;
  }
}

let refreshPromise: Promise<void> | null = null;

async function refreshToken(): Promise<void> {
  const res = await fetch("/api/v1/lti/jwt-refresh", {
    method: "POST",
    credentials: "include",
  });

  if (!res.ok) {
    throw new ApiError(res.status, "Refresh failed");
  }
}

function isJwtError(body: unknown): boolean {
  return (
    typeof body === "object" &&
    body !== null &&
    "error_type" in body &&
    body.error_type === "JWTDecodeError"
  );
}

export async function apiFetch<T>(
  url: string,
  options: RequestInit = {},
  retry = true,
): Promise<T> {
  const isFormData = options.body instanceof FormData;
  const res = await fetch(url, {
    ...options,
    credentials: "include",
    headers: isFormData
      ? options.headers
      : {
          "Content-Type": "application/json",
          ...options.headers,
        },
  });

  const body = res.status !== 204 ? await res.json().catch(() => null) : null;

  if (!res.ok) {
    if (res.status === 401 && isJwtError(body) && retry) {
      if (!refreshPromise) {
        refreshPromise = refreshToken().finally(() => {
          refreshPromise = null;
        });
      }
      await refreshPromise;
      return apiFetch<T>(url, options, false);
    }

    throw new ApiError(res.status, res.statusText, body);
  }

  if (res.status === 204) return {} as T;
  return body as T;
}
