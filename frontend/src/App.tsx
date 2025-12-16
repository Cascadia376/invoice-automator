import { Toaster } from "@/components/ui/toaster";
import { Toaster as Sonner } from "@/components/ui/sonner";
import { TooltipProvider } from "@/components/ui/tooltip";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { InvoiceProvider } from "@/context/InvoiceContext";
import { DashboardLayout } from "@/components/layout/DashboardLayout";
import Index from "./pages/Index";
import Dashboard from "./pages/Dashboard";
import Upload from "./pages/Upload";
import InvoiceReview from "./pages/InvoiceReview";
import Settings from "./pages/Settings";
import Vendors from "./pages/Vendors";
import VendorDetail from "./pages/VendorDetail";
import NotFound from "./pages/NotFound";

const queryClient = new QueryClient();

import { ClerkProvider, SignedIn, SignedOut, RedirectToSignIn } from "@clerk/clerk-react";

const App = () => {
  const PUBLISHABLE_KEY = import.meta.env.VITE_CLERK_PUBLISHABLE_KEY || import.meta.env.NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY

  if (!PUBLISHABLE_KEY) {
    return (
      <div className="flex h-screen items-center justify-center bg-red-50 p-4">
        <div className="text-center">
          <h1 className="text-2xl font-bold text-red-800 mb-2">Configuration Error</h1>
          <p className="text-red-600">Missing Clerk Publishable Key.</p>
          <p className="text-sm text-gray-600 mt-4">
            Please add <code className="bg-gray-200 px-1 rounded">VITE_CLERK_PUBLISHABLE_KEY</code> to your frontend <code className="bg-gray-200 px-1 rounded">.env</code> file.
          </p>
        </div>
      </div>
    )
  }

  return (
    <ClerkProvider publishableKey={PUBLISHABLE_KEY}>
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
                <Route
                  path="/*"
                  element={
                    <>
                      <SignedIn>
                        <Routes>
                          <Route element={<DashboardLayout />}>
                            <Route path="/dashboard" element={<Dashboard />} />
                            <Route path="/upload" element={<Upload />} />
                            <Route path="/invoices" element={<Navigate to="/dashboard" replace />} />
                            <Route path="/vendors" element={<Vendors />} />
                            <Route path="/settings" element={<Settings />} />
                          </Route>

                          <Route path="/invoices/:id" element={<InvoiceReview />} />
                          <Route path="/vendors/:vendorId" element={<VendorDetail />} />

                          {/* Catch-all for protected routes */}
                          <Route path="*" element={<NotFound />} />
                        </Routes>
                      </SignedIn>
                      <SignedOut>
                        <RedirectToSignIn />
                      </SignedOut>
                    </>
                  }
                />
              </Routes>
            </BrowserRouter>
          </InvoiceProvider>
        </TooltipProvider>
      </QueryClientProvider>
    </ClerkProvider>
  );
};

export default App;
