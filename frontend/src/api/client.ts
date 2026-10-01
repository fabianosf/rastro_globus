const TOKEN_KEY = "rg_access";
const REFRESH_KEY = "rg_refresh";
const USER_KEY = "rg_user";

export type User = {
  id: number;
  username: string;
  first_name: string;
  last_name: string;
  email: string;
  perfil: string;
  telefone: string;
};

export function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY);
}

export function getStoredUser(): User | null {
  const raw = localStorage.getItem(USER_KEY);
  if (!raw) return null;
  try {
    return JSON.parse(raw) as User;
  } catch {
    return null;
  }
}

export function setSession(access: string, refresh: string, user: User) {
  localStorage.setItem(TOKEN_KEY, access);
  localStorage.setItem(REFRESH_KEY, refresh);
  localStorage.setItem(USER_KEY, JSON.stringify(user));
}

export function clearSession() {
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(REFRESH_KEY);
  localStorage.removeItem(USER_KEY);
}

type RequestOptions = {
  method?: string;
  body?: unknown;
  formData?: FormData;
  auth?: boolean;
};

export class ApiError extends Error {
  status: number;
  constructor(message: string, status: number) {
    super(message);
    this.status = status;
  }
}

export async function api<T = unknown>(path: string, options: RequestOptions = {}): Promise<T> {
  const headers: Record<string, string> = {};
  const auth = options.auth !== false;
  const token = getToken();
  if (auth && token) {
    headers.Authorization = `Bearer ${token}`;
  }

  let body: BodyInit | undefined;
  if (options.formData) {
    body = options.formData;
  } else if (options.body !== undefined) {
    headers["Content-Type"] = "application/json";
    body = JSON.stringify(options.body);
  }

  const res = await fetch(path.startsWith("/api") ? path : `/api${path}`, {
    method: options.method || "GET",
    headers,
    body,
  });

  if (res.status === 204) {
    return undefined as T;
  }

  const contentType = res.headers.get("content-type") || "";
  if (contentType.includes("text/csv") || contentType.includes("application/octet-stream")) {
    if (!res.ok) {
      throw new ApiError("Falha ao baixar arquivo.", res.status);
    }
    return (await res.blob()) as T;
  }

  const data = contentType.includes("application/json") ? await res.json() : await res.text();

  if (!res.ok) {
    const detail =
      typeof data === "object" && data && "detail" in data
        ? String((data as { detail: unknown }).detail)
        : typeof data === "string"
          ? data
          : "Erro na requisição.";
    throw new ApiError(detail, res.status);
  }

  return data as T;
}

export async function login(username: string, password: string) {
  const data = await api<{ access: string; refresh: string; user: User }>("/api/auth/login/", {
    method: "POST",
    body: { username, password },
    auth: false,
  });
  setSession(data.access, data.refresh, data.user);
  return data;
}
