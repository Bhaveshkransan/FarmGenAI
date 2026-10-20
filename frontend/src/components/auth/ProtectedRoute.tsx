import React from 'react';
import { Navigate, Outlet } from 'react-router-dom';
import { useAuth } from '../../contexts/AuthContext';

/**
 * Enterprise RBAC Route Guard
 * Validates authentication status and checks if the user's role exists in allowedRoles.
 * 
 * @param {Array<string>} allowedRoles - Array of roles permitted to access this route
 */
export default function ProtectedRoute({ allowedRoles = [] }) {
  const { user, loading } = useAuth();

  // If AuthContext is still fetching tokens on hard reload, show generic loading state
  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-50 text-emerald-600 font-bold tracking-widest uppercase">
        Authenticating...
      </div>
    );
  }

  // Not logged in -> Redirect to login page
  if (!user) {
    return <Navigate to="/login" replace />;
  }

  // Role validation (case-insensitive)
  const userRole = user.role?.toLowerCase();
  const isAllowed = allowedRoles.length === 0 || allowedRoles.some(r => r.toLowerCase() === userRole);

  // Wrong role → silently redirect to their own dashboard (no 403 error page)
  if (!isAllowed) {
    return <Navigate to="/dashboard" replace />;
  }

  // All checks passed, render the nested routes
  return <Outlet />;
}
