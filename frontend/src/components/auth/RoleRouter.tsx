import React from 'react';
import { Navigate } from 'react-router-dom';
import { useAuth } from '../../contexts/AuthContext';

export default function RoleRouter() {
  const { user } = useAuth();

  if (!user) {
    return <Navigate to="/login" replace />;
  }

  // Redirect based on role
  switch (user.role?.toLowerCase()) {
    case 'farmer':
      return <Navigate to="/dashboard/farmer" replace />;
    case 'buyer':
      return <Navigate to="/dashboard/buyer" replace />;
    case 'warehouse':
      return <Navigate to="/dashboard/warehouse" replace />;
    case 'transport':
    case 'transporter':
      return <Navigate to="/dashboard/transport" replace />;
    case 'processor':
      return <Navigate to="/dashboard/processor" replace />;
    case 'admin':
      return <Navigate to="/dashboard/admin" replace />;
    default:
      return <Navigate to="/dashboard/farmer" replace />;
  }
}
