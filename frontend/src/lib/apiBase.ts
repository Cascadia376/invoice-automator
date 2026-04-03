const LOCAL_API_BASE = "http://localhost:8000";

export function getApiBaseUrl(): string {
  const configuredBase =
    import.meta.env.VITE_API_BASE || import.meta.env.VITE_API_URL;

  if (configuredBase) {
    return configuredBase;
  }

  if (typeof window !== "undefined" && import.meta.env.PROD) {
    return window.location.origin;
  }

  return LOCAL_API_BASE;
}
