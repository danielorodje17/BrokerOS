import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import axios from 'axios';

const AuthContext = createContext(null);

const API = process.env.REACT_APP_BACKEND_URL + '/api';

// Configure axios defaults
axios.defaults.withCredentials = true;

function formatApiErrorDetail(detail) {
  if (detail == null) return "Something went wrong. Please try again.";
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail))
    return detail.map((e) => (e && typeof e.msg === "string" ? e.msg : JSON.stringify(e))).filter(Boolean).join(" ");
  if (detail && typeof detail.msg === "string") return detail.msg;
  return String(detail);
}

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null); // null = checking, false = not authenticated
  const [loading, setLoading] = useState(true);

  const checkAuth = useCallback(async () => {
    try {
      const { data } = await axios.get(`${API}/auth/me`, { withCredentials: true });
      setUser(data);
    } catch (error) {
      // Try to refresh token
      try {
        await axios.post(`${API}/auth/refresh`, {}, { withCredentials: true });
        const { data } = await axios.get(`${API}/auth/me`, { withCredentials: true });
        setUser(data);
      } catch {
        setUser(false);
      }
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    checkAuth();
  }, [checkAuth]);

  const login = async (email, password) => {
    try {
      const { data } = await axios.post(`${API}/auth/login`, { email, password }, { withCredentials: true });
      setUser(data);
      return { success: true, data };
    } catch (error) {
      return { success: false, error: formatApiErrorDetail(error.response?.data?.detail) };
    }
  };

  const register = async (email, password, first_name, last_name) => {
    try {
      const { data } = await axios.post(`${API}/auth/register`, { email, password, first_name, last_name }, { withCredentials: true });
      setUser(data);
      return { success: true, data };
    } catch (error) {
      return { success: false, error: formatApiErrorDetail(error.response?.data?.detail) };
    }
  };

  const logout = async () => {
    try {
      await axios.post(`${API}/auth/logout`, {}, { withCredentials: true });
    } catch (error) {
      console.error('Logout error:', error);
    }
    setUser(false);
  };

  const forgotPassword = async (email) => {
    try {
      await axios.post(`${API}/auth/forgot-password`, { email });
      return { success: true };
    } catch (error) {
      return { success: false, error: formatApiErrorDetail(error.response?.data?.detail) };
    }
  };

  const resetPassword = async (token, newPassword) => {
    try {
      await axios.post(`${API}/auth/reset-password`, { token, new_password: newPassword });
      return { success: true };
    } catch (error) {
      return { success: false, error: formatApiErrorDetail(error.response?.data?.detail) };
    }
  };

  const updateProfile = async (data) => {
    try {
      const { data: updated } = await axios.put(`${API}/users/me`, data, { withCredentials: true });
      setUser(prev => ({ ...prev, ...updated }));
      return { success: true, data: updated };
    } catch (error) {
      return { success: false, error: formatApiErrorDetail(error.response?.data?.detail) };
    }
  };

  const completeOnboarding = async () => {
    try {
      await axios.put(`${API}/users/me/onboarding`, {}, { withCredentials: true });
      setUser(prev => ({ ...prev, onboarding_completed: true }));
      return { success: true };
    } catch (error) {
      return { success: false, error: formatApiErrorDetail(error.response?.data?.detail) };
    }
  };

  return (
    <AuthContext.Provider value={{
      user,
      loading,
      login,
      register,
      logout,
      forgotPassword,
      resetPassword,
      updateProfile,
      completeOnboarding,
      checkAuth
    }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}
