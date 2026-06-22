import axios from "axios";
import { useAuthStore } from "../store/auth";

const API_BASE_URL = "https://api.condobuddy2.local/api/v1"; // Update for production

const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 15000,
  headers: {
    "Content-Type": "application/json",
  },
});

api.interceptors.request.use(async (config) => {
  const token = useAuthStore.getState().token;
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    if (error.response?.status === 401) {
      useAuthStore.getState().logout();
    }
    return Promise.reject(error);
  }
);

export default api;

// Auth
export const login = (email: string, password: string) =>
  api.post("/auth/login", new URLSearchParams({ username: email, password }));

export const register = (data: any) => api.post("/auth/register", data);
export const getMe = () => api.get("/auth/me");

// Work Orders
export const listWorkOrders = (params?: any) => api.get("/work-orders", { params });
export const createWorkOrder = (data: any) => api.post("/work-orders", data);
export const updateWorkOrder = (id: string, data: any) => api.patch(`/work-orders/${id}`, data);

// Visitors
export const listVisitors = (params?: any) => api.get("/visitors", { params });
export const createVisitor = (data: any) => api.post("/visitors", data);

// Packages
export const listPackages = (params?: any) => api.get("/packages", { params });
export const pickupPackage = (id: string, code: string) =>
  api.post(`/packages/${id}/pickup`, { access_code: code });

// Access
export const listAccessLogs = (params?: any) => api.get("/access/logs", { params });

// Facility Bookings
export const listBookings = (params?: any) => api.get("/facility-bookings", { params });
export const createBooking = (data: any) => api.post("/facility-bookings", data);
export const listFacilities = () => api.get("/facility-bookings/facilities/available");

// Notifications (WebSocket)
export const connectWebSocket = (token: string) => {
  const wsUrl = API_BASE_URL.replace("https://", "wss://").replace("http://", "ws://");
  return new WebSocket(`${wsUrl}/notifications/ws/${token}`);
};
