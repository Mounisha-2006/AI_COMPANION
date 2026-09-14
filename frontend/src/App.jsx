import React from 'react';
import { BrowserRouter, Routes, Route, Navigate, Outlet } from 'react-router-dom';
import { AuthProvider } from './context/AuthContext';
import { ProtectedRoute } from './components/ProtectedRoute';
import { AdminRoute } from './components/AdminRoute';
import { Sidebar } from './components/Sidebar';
import { LoginPage } from './pages/LoginPage';
import { RegisterPage } from './pages/RegisterPage';
import { DashboardPage } from './pages/DashboardPage';
import { SpacesPage } from './pages/SpacesPage';
import { SpaceDetailPage } from './pages/SpaceDetailPage';
import { ProjectDetailPage } from './pages/ProjectDetailPage';
import { AssessmentPage } from './pages/AssessmentPage';
import { GlobalAnalyticsPage } from './pages/GlobalAnalyticsPage';
import { AdminDashboardPage } from './pages/AdminDashboardPage';

function AppLayout() {
  return (
    <div className="app-container">
      <Sidebar />
      <main className="main-content">
        <Outlet />
      </main>
    </div>
  );
}

export function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          {/* Public routes */}
          <Route path="/login" element={<LoginPage />} />
          <Route path="/register" element={<RegisterPage />} />

          {/* Protected routes */}
          <Route
            element={
              <ProtectedRoute>
                <AppLayout />
              </ProtectedRoute>
            }
          >
            <Route path="/dashboard" element={<DashboardPage />} />
            <Route path="/analytics" element={<GlobalAnalyticsPage />} />
            <Route path="/spaces" element={<SpacesPage />} />
            <Route path="/spaces/:spaceId" element={<SpaceDetailPage />} />
            <Route path="/projects/:projectId" element={<ProjectDetailPage />} />
            <Route path="/projects/:projectId/assessment" element={<AssessmentPage />} />
            <Route
              path="/admin"
              element={
                <AdminRoute>
                  <AdminDashboardPage />
                </AdminRoute>
              }
            />
          </Route>

          {/* Fallback routes */}
          <Route path="/" element={<Navigate to="/dashboard" replace />} />
          <Route path="*" element={<Navigate to="/dashboard" replace />} />
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  );
}

export default App;
