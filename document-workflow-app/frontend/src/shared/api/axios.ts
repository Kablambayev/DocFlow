import axios from "axios";

export const apiClient = axios.create({
  baseURL:
    import.meta.env.VITE_API_BASE_URL ??
    import.meta.env.VITE_API_URL ??
    "http://127.0.0.1:8000/api/v1",
  timeout: 15000,
});

export const setUserIdHeader = (userId: string | null) => {
  if (userId) {
    apiClient.defaults.headers.common["X-User-Id"] = userId;
    localStorage.setItem("docflow_user_id", userId);
  } else {
    delete apiClient.defaults.headers.common["X-User-Id"];
    localStorage.removeItem("docflow_user_id");
  }
};

const storedUserId = localStorage.getItem("docflow_user_id");
if (storedUserId) {
  apiClient.defaults.headers.common["X-User-Id"] = storedUserId;
}

