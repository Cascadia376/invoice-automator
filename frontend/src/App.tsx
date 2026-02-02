import { Toaster } from "@/components/ui/toaster";
import { Toaster as Sonner } from "@/components/ui/sonner";
import { TooltipProvider } from "@/components/ui/tooltip";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter, Routes, Route, Navigate, Outlet } from "react-router-dom";
import { InvoiceProvider } from "@/context/InvoiceContext";
import { DashboardLayout } from "@/components/layout/DashboardLayout";
import Index from "./pages/Index";
import Dashboard from "./pages/Dashboard";
import Upload from "./pages/Upload";
import InvoiceReview from "./pages/InvoiceReview";
import PDFViewOnly from "./pages/PDFViewOnly";
import Settings from "./pages/Settings";
import Vendors from "./pages/Vendors";
import IssueTracker from "./pages/IssueTracker";
import VendorDetail from "./pages/VendorDetail";
import APSageView from "./pages/APSageView";
import APPosView from "./pages/APPosView";
import NotFound from "./pages/NotFound";
import Reports from "./pages/Reports";
import SmokeTest from "./pages/SmokeTest";
import { AuthProvider, useAuth } from "@/context/AuthContext";

const queryClient = new QueryClient();

const RequireAuth = () => {
  const { loading, session, disableAuth } = useAuth();

  if (disableAuth) {
    return <Outlet />;
  }

  if (loading) {
    return (
      <div className="flex h-screen items-center justify-center bg-gray-50">
        <div className="text-gray-700">Loading...</div>
      </div>
    );
  }

  if (!session) {
    return <Navigate to="/" replace />;
  }

  return <Outlet />;
};

const RequireRole = ({ role }: { role: string }) => {
  const { loading, roles, isAdmin } = useAuth();

  if (loading) return <div>Loading...</div>;

  if (role === 'admin' && !isAdmin) {
    return <Navigate to="/dashboard" replace />;
  }

  if (!roles.includes(role) && !isAdmin) {
    return <Navigate to="/dashboard" replace />;
  }

  return <Outlet />;
};

const App = () => {
  return (
    <AuthProvider>
      <QueryClientProvider client={queryClient}>
        <TooltipProvider>
          <InvoiceProvider>
            <Toaster />
            <Sonner />
            <BrowserRouter>
              <Routes>
                {/* Public Routes */}
                <Route path="/" element={<Index />} />

                {/* Protected Routes */}
                <Route element={<RequireAuth />}>
                  <Route element={<DashboardLayout />}>
                    <Route path="/dashboard" element={<Dashboard />} />
                    <Route path="/issues" element={<IssueTracker />} />
                    <Route path="/upload" element={<Upload />} />
                    <Route path="/invoices" element={<Navigate to="/dashboard" replace />} />
                    <Route path="/vendors" element={<Vendors />} />
                    <Route path="/ap-view" element={<APSageView />} />
                    <Route path="/ap-pos-view" element={<APPosView />} />
                    <Route path="/reports" element={<Reports />} />
                    <Route path="/smoke-test" element={<SmokeTest />} />
                    <Route element={<RequireRole role="admin" />}>
                      <Route path="/settings" element={<Settings />} />
                    </Route>
                  </Route>
                  <Route path="/invoices/:id" element={<InvoiceReview />} />
                  <Route path="/invoices/:id/pdf" element={<PDFViewOnly />} />
                  <Route path="/vendors/:vendorId" element={<VendorDetail />} />
                  <Route path="*" element={<NotFound />} />
                </Route>
              </Routes>
            </BrowserRouter>
          </InvoiceProvider>
        </TooltipProvider>
      </QueryClientProvider>
    </AuthProvider>
  );
};

export default App;
