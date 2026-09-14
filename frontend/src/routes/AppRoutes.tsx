import React, { Suspense, lazy } from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import ProtectedRoute from '@/components/auth/ProtectedRoute';
import RoleRouter from '@/components/auth/RoleRouter';
import PageLoader from '@/components/ui/PageLoader';

// Layouts
import DashboardLayout from '@/layouts/DashboardLayout';

// ── Auth Pages ────────────────────────────────────────────
const Login = lazy(() => import('@/pages/auth/Login'));
const Register = lazy(() => import('@/pages/auth/Register'));

// ── Public Pages ──────────────────────────────────────────
const LandingPage = lazy(() => import('@/pages/public/LandingPage'));
const AboutPage = lazy(() => import('@/pages/public/AboutPage'));

// ── Role Dashboards ───────────────────────────────────────
const FarmerDashboard = lazy(() => import('@/pages/farmer/FarmerDashboard'));
const BuyerDashboard = lazy(() => import('@/pages/buyer/BuyerDashboard'));
const WarehouseDashboard = lazy(() => import('@/pages/warehouse/WarehouseDashboard'));
const TransportDashboard = lazy(() => import('@/pages/transport/TransportDashboard'));
const ProcessorDashboard = lazy(() => import('@/pages/processor/ProcessorDashboard'));
const AdminDashboard = lazy(() => import('@/pages/admin/AdminDashboard'));
const AIOperationsCenter = lazy(() => import('@/pages/admin/AIOperationsCenter'));
const SettingsDashboard = lazy(() => import('@/pages/admin/SettingsDashboard'));

// ── Shared Pages ──────────────────────────────────────────
const NegotiationRoom = lazy(() => import('@/pages/negotiation/NegotiationRoom'));
const DealTracker = lazy(() => import('@/pages/logistics/DealTracker'));
const GlobalAnalytics = lazy(() => import('@/pages/analytics/GlobalAnalytics'));
const UserProfile = lazy(() => import('@/pages/profile/UserProfile'));
const TransactionsPage = lazy(() => import('@/pages/transactions/TransactionsPage'));

// ── Error Pages ───────────────────────────────────────────
const NotFound = lazy(() => import('@/pages/errors/NotFoundPage'));

/**
 * Enterprise Application Routing Module.
 * Extracted from App.jsx to enforce Clean Architecture and separation of concerns.
 */
export default function AppRoutes() {
  return (
    <Suspense fallback={<PageLoader />}>
      <Routes>
        {/* Public Routes */}
        <Route path="/" element={<LandingPage />} />
        <Route path="/about" element={<AboutPage />} />
        <Route path="/login" element={<Login />} />
        <Route path="/register" element={<Register />} />

        {/* Top-Level Role Aliases */}
        <Route path="/buyer" element={<Navigate to="/dashboard/buyer" replace />} />
        <Route path="/farmer" element={<Navigate to="/dashboard/farmer" replace />} />
        <Route path="/warehouse" element={<Navigate to="/dashboard/warehouse" replace />} />
        <Route path="/transport" element={<Navigate to="/dashboard/transport" replace />} />
        <Route path="/processor" element={<Navigate to="/dashboard/processor" replace />} />
        
        {/* Protected Routes Wrapper */}
        <Route element={<DashboardLayout />}>
          
          {/* Master Route Router */}
          <Route path="/dashboard" element={<RoleRouter />} />

          {/* Alias Routes — Protected: any authenticated role */}
          <Route element={<ProtectedRoute allowedRoles={['farmer', 'buyer', 'warehouse', 'transport', 'processor', 'admin']} />}>
            <Route path="/buyer" element={<Navigate to="/dashboard/buyer" replace />} />
            <Route path="/farmer" element={<Navigate to="/dashboard/farmer" replace />} />
            <Route path="/warehouse" element={<Navigate to="/dashboard/warehouse" replace />} />
            <Route path="/transport" element={<Navigate to="/dashboard/transport" replace />} />
            <Route path="/processor" element={<Navigate to="/dashboard/processor" replace />} />
            <Route path="/farmer/listings" element={<Navigate to="/dashboard/farmer" replace />} />
            <Route path="/farmer/listings/new" element={<Navigate to="/dashboard/farmer" replace />} />
            <Route path="/farmer/negotiations" element={<Navigate to="/dashboard/farmer" replace />} />
            <Route path="/farmer/transactions" element={<Navigate to="/transactions" replace />} />
            <Route path="/buyer/requirements" element={<Navigate to="/dashboard/buyer" replace />} />
            <Route path="/buyer/requirements/new" element={<Navigate to="/dashboard/buyer" replace />} />
            <Route path="/buyer/matches" element={<Navigate to="/dashboard/buyer" replace />} />
            <Route path="/buyer/negotiations" element={<Navigate to="/dashboard/buyer" replace />} />
            <Route path="/buyer/transactions" element={<Navigate to="/transactions" replace />} />
          </Route>

          {/* Role-Gated Dashboards */}
          <Route element={<ProtectedRoute allowedRoles={['farmer', 'admin']} />}>
            <Route path="/dashboard/farmer" element={<FarmerDashboard />} />
          </Route>
          <Route element={<ProtectedRoute allowedRoles={['buyer', 'admin']} />}>
            <Route path="/dashboard/buyer" element={<BuyerDashboard />} />
          </Route>
          <Route element={<ProtectedRoute allowedRoles={['warehouse', 'admin']} />}>
            <Route path="/dashboard/warehouse" element={<WarehouseDashboard />} />
          </Route>
          <Route element={<ProtectedRoute allowedRoles={['transport', 'admin']} />}>
            <Route path="/dashboard/transport" element={<TransportDashboard />} />
          </Route>
          <Route element={<ProtectedRoute allowedRoles={['processor', 'admin']} />}>
            <Route path="/dashboard/processor" element={<ProcessorDashboard />} />
          </Route>
          <Route element={<ProtectedRoute allowedRoles={['admin']} />}>
            <Route path="dashboard/admin" element={<AdminDashboard />} />
            <Route path="dashboard/ai-ops" element={<AIOperationsCenter />} />
            <Route path="dashboard/settings" element={<SettingsDashboard />} />
          </Route>

          {/* Shared Features */}
          <Route element={<ProtectedRoute allowedRoles={['farmer', 'buyer', 'warehouse', 'transport', 'processor', 'admin']} />}>
            <Route path="/profile" element={<UserProfile />} />
            <Route path="/analytics" element={<GlobalAnalytics />} />
            <Route path="/transactions" element={<TransactionsPage />} />
            
            {/* New Prompt Aliases */}
            <Route path="/negotiations/:id" element={<NegotiationRoom />} />
            <Route path="/supply-chain/:id" element={<DealTracker />} />
            
            {/* Original Paths */}
            <Route path="/negotiation/:id" element={<NegotiationRoom />} />
            <Route path="/deal/:id/track" element={<DealTracker />} />
          </Route>

          {/* Fallback */}
          <Route path="*" element={<NotFound />} />
        </Route>
      </Routes>
    </Suspense>
  );
}
