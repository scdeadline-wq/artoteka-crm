import axios from "axios";

const api = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000",
});

api.interceptors.request.use((config) => {
  if (typeof window !== "undefined") {
    const token = localStorage.getItem("token");
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
  }
  // Ensure trailing slash to avoid 307 redirects from FastAPI
  if (config.url && !config.url.includes("?") && !config.url.endsWith("/")) {
    config.url += "/";
  }
  return config;
});

api.interceptors.response.use(
  (res) => res,
  (err) => {
    // Не редиректим при ошибке самого логина — страница должна показать «Неверный логин или пароль»
    const isLoginRequest = err.config?.url?.includes("/auth/login");
    if (err.response?.status === 401 && !isLoginRequest && typeof window !== "undefined") {
      localStorage.removeItem("token");
      window.location.href = "/login";
    }
    return Promise.reject(err);
  }
);

export default api;
