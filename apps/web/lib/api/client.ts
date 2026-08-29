const API_URL = (process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000").replace(
  /\/$/,
  "",
);

export class ApiError extends Error {
  constructor(
    message: string,
    public readonly status: number,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

function readErrorMessage(body: unknown): string | null {
  if (!body || typeof body !== "object" || !("detail" in body)) {
    return null;
  }

  const detail = body.detail;
  if (typeof detail === "string") {
    return detail;
  }

  return null;
}

export async function apiRequest<T>(
  path: string,
  init?: RequestInit,
): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`${API_URL}${path}`, {
      ...init,
      headers: {
        Accept: "application/json",
        "Content-Type": "application/json",
        ...init?.headers,
      },
    });
  } catch {
    throw new ApiError(
      "Lead Radar could not reach the discovery service. Check that the API is running and try again.",
      0,
    );
  }

  const body: unknown = await response.json().catch(() => null);
  if (!response.ok) {
    throw new ApiError(
      readErrorMessage(body) ?? "The discovery service could not complete this request.",
      response.status,
    );
  }

  return body as T;
}

export async function apiBlobRequest(
  path: string,
  init?: RequestInit,
): Promise<{ blob: Blob; filename: string | null }> {
  let response: Response;
  try {
    response = await fetch(`${API_URL}${path}`, {
      ...init,
      headers: {
        Accept: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "Content-Type": "application/json",
        ...init?.headers,
      },
    });
  } catch {
    throw new ApiError("Lead Radar could not reach the export service.", 0);
  }
  if (!response.ok) {
    const body: unknown = await response.json().catch(() => null);
    throw new ApiError(
      readErrorMessage(body) ?? "The Excel export could not be generated.",
      response.status,
    );
  }
  const disposition = response.headers.get("content-disposition");
  const filename = disposition?.match(/filename="?([^";]+)"?/i)?.[1] ?? null;
  return { blob: await response.blob(), filename };
}

