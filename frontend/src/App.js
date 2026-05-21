import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider, useAuth } from './contexts/AuthContext';
import { ProtectedRoute } from './components/ProtectedRoute';
import { Layout } from './components/Layout';
import { Login } from './pages/Login';
import { Register } from './pages/Register';
import { ForgotPassword } from './pages/ForgotPassword';
import { Onboarding } from './pages/Onboarding';
import { Dashboard } from './pages/Dashboard';
import { Clients } from './pages/Clients';
import { Cases } from './pages/Cases';
import { Pipeline } from './pages/Pipeline';
import { Lenders } from './pages/Lenders';
import { Commissions } from './pages/Commissions';
import { Settings } from './pages/Settings';
import './App.css';

function OnboardingCheck({ children }) {
  const { user } = useAuth();
  
  // If user hasn't completed onboarding and it's their first login
  if (user && !user.onboarding_completed) {
    return <Navigate to="/onboarding" replace />;
  }
  
  return children;
}

function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          {/* Public routes */}
          <Route path="/login" element={<Login />} />
          <Route path="/register" element={<Register />} />
          <Route path="/forgot-password" element={<ForgotPassword />} />
          
          {/* Onboarding (protected but separate) */}
          <Route path="/onboarding" element={
            <ProtectedRoute>
              <Onboarding />
            </ProtectedRoute>
          } />
          
          {/* Protected routes with layout */}
          <Route path="/" element={
            <ProtectedRoute>
              <OnboardingCheck>
                <Layout />
              </OnboardingCheck>
            </ProtectedRoute>
          }>
            <Route index element={<Navigate to="/dashboard" replace />} />
            <Route path="dashboard" element={<Dashboard />} />
            <Route path="clients" element={<Clients />} />
            <Route path="cases" element={<Cases />} />
            <Route path="pipeline" element={<Pipeline />} />
            <Route path="lenders" element={<Lenders />} />
            <Route path="commissions" element={<Commissions />} />
            <Route path="settings" element={<Settings />} />
          </Route>
          
          {/* Catch all */}
          <Route path="*" element={<Navigate to="/dashboard" replace />} />
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  );
}

export default App;
