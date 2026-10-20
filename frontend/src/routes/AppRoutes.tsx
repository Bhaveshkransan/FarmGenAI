import React, { Suspense, lazy } from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import ProtectedRoute from '@/components/auth/ProtectedRoute';
import RoleRouter from '@/components/auth/RoleRouter';
import PageLoader from '@/components/ui/PageLoader';

// Layouts
import FarmerLayout from '@/layouts/FarmerLayout';
import BuyerLayout from '@/layouts/BuyerLayout';
import WarehouseLayout from '@/layouts/WarehouseLayout';
import TransportLayout from '@/layouts/TransportLayout';
import ProcessorLayout from '@/layouts/ProcessorLayout';
import AdminLayout from '@/layouts/AdminLayout';
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
const TransportNegotiationRoom = lazy(() => import('@/pages/transport/TransportNegotiationRoom'));
const TransporterDashboard = lazy(() => import('@/pages/transport/TransporterDashboard'));
const TransportTransactions = lazy(() => import('@/pages/transport/TransportTransactions'));
const TransportMarketAnalysis = lazy(() => import('@/pages/transport/TransportMarketAnalysis'));
const VehicleList = lazy(() => import('@/pages/transport/VehicleList'));
const VehicleDetail = lazy(() => import('@/pages/transport/VehicleDetail'));
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
        
        {/* Master Route Router */}
        <Route path="/dashboard" element={<RoleRouter />} />

        {/* ── Direct Route Aliases & Role Shortcuts ────────────────────────── */}
        <Route path="/buyer" element={<Navigate to="/dashboard/buyer" replace />} />
        <Route path="/farmer" element={<Navigate to="/dashboard/farmer" replace />} />
        <Route path="/warehouse" element={<Navigate to="/dashboard/warehouse" replace />} />
        <Route path="/transport" element={<Navigate to="/dashboard/transport" replace />} />
        <Route path="/processor" element={<Navigate to="/dashboard/processor" replace />} />
        <Route path="/admin" element={<Navigate to="/dashboard/admin" replace />} />

        {/* ── Role-Specific Main Dashboards ───────────────────────────────── */}
        {/* Farmer Dashboard */}
        <Route element={<FarmerLayout />}>
          <Route element={<ProtectedRoute allowedRoles={['farmer', 'admin']} />}>
            <Route path="/dashboard/farmer" element={<FarmerDashboard />} />
            <Route path="/farmer/dashboard" element={<Navigate to="/dashboard/farmer" replace />} />
            <Route path="/farmer/listings" element={<Navigate to="/dashboard/farmer" replace />} />
            <Route path="/farmer/listings/new" element={<Navigate to="/dashboard/farmer" replace />} />
          </Route>
        </Route>

        {/* Buyer Dashboard */}
        <Route element={<BuyerLayout />}>
          <Route element={<ProtectedRoute allowedRoles={['buyer', 'admin']} />}>
            <Route path="/dashboard/buyer" element={<BuyerDashboard />} />
            <Route path="/buyer/dashboard" element={<Navigate to="/dashboard/buyer" replace />} />
            <Route path="/buyer/agent" element={<Navigate to="/dashboard/buyer" replace />} />
            <Route path="/buyer/requirements" element={<Navigate to="/dashboard/buyer" replace />} />
            <Route path="/buyer/requirements/new" element={<Navigate to="/dashboard/buyer" replace />} />
            <Route path="/buyer/matches" element={<Navigate to="/dashboard/buyer" replace />} />
          </Route>
        </Route>

        {/* Warehouse Dashboard */}
        <Route element={<WarehouseLayout />}>
          <Route element={<ProtectedRoute allowedRoles={['warehouse', 'admin']} />}>
            <Route path="/dashboard/warehouse" element={<WarehouseDashboard />} />
            <Route path="/warehouse/dashboard" element={<Navigate to="/dashboard/warehouse" replace />} />
          </Route>
        </Route>

        {/* Transport Dashboard */}
        <Route element={<TransportLayout />}>
          <Route element={<ProtectedRoute allowedRoles={['transport', 'admin']} />}>
            <Route path="/dashboard/transport" element={<TransportDashboard />} />
            <Route path="/dashboard/transport/negotiation" element={<TransportNegotiationRoom />} />
            <Route path="/dashboard/transport/transactions" element={<TransportTransactions />} />
            <Route path="/dashboard/transport/analytics" element={<TransportMarketAnalysis />} />
            <Route path="/transport/dashboard" element={<Navigate to="/dashboard/transport" replace />} />
            <Route path="/transport/negotiate" element={<Navigate to="/dashboard/transport/negotiation" replace />} />
            <Route path="/transport/:id" element={<VehicleDetail />} />
            <Route path="/transporter" element={<TransporterDashboard />} />
            <Route path="/transporter/vehicles" element={<VehicleList />} />
            <Route path="/transporter/vehicles/:id" element={<VehicleDetail />} />
          </Route>
        </Route>

        {/* Processor Dashboard */}
        <Route element={<ProcessorLayout />}>
          <Route element={<ProtectedRoute allowedRoles={['processor', 'admin']} />}>
            <Route path="/dashboard/processor" element={<ProcessorDashboard />} />
            <Route path="/processor/dashboard" element={<Navigate to="/dashboard/processor" replace />} />
          </Route>
        </Route>

        {/* Admin Dashboard */}
        <Route element={<AdminLayout />}>
          <Route element={<ProtectedRoute allowedRoles={['admin']} />}>
            <Route path="/dashboard/ai-ops" element={<AIOperationsCenter />} />
            <Route path="/dashboard/admin" element={<AdminDashboard />} />
            <Route path="/dashboard/settings" element={<SettingsDashboard />} />
            <Route path="/admin/dashboard" element={<Navigate to="/dashboard/admin" replace />} />
          </Route>
        </Route>

        {/* ── Dynamic Authenticated Shared Pages (Adapts sidebar to user's role) ── */}
        <Route element={<DashboardLayout />}>
          <Route element={<ProtectedRoute />}>
            <Route path="/profile" element={<UserProfile />} />
            <Route path="/analytics" element={<GlobalAnalytics />} />
            <Route path="/transactions" element={<TransactionsPage />} />
            
            {/* AI Multi-Agent Negotiation Routes */}
            <Route path="/negotiations" element={<NegotiationRoom />} />
            <Route path="/negotiation" element={<NegotiationRoom />} />
            <Route path="/negotiations/:id" element={<NegotiationRoom />} />
            <Route path="/negotiation/:id" element={<NegotiationRoom />} />
            <Route path="/buyer/negotiations" element={<NegotiationRoom />} />
            <Route path="/farmer/negotiations" element={<NegotiationRoom />} />
            <Route path="/buyer/negotiations/:id" element={<NegotiationRoom />} />
            <Route path="/farmer/negotiations/:id" element={<NegotiationRoom />} />

            {/* Logistics & Deal Tracking */}
            <Route path="/supply-chain/:id" element={<DealTracker />} />
            <Route path="/deal/:id/track" element={<DealTracker />} />
          </Route>
        </Route>

        {/* Fallback */}
        <Route path="*" element={<NotFound />} />
      </Routes>
    </Suspense>
  );
}
