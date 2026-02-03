import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import { useAuth } from "@/context/AuthContext";
import { Invoice, DashboardStats, GLCategory } from '@/types/invoice';
import { toast } from 'sonner';

interface InvoiceContextType {
    invoices: Invoice[];
    stats: DashboardStats;
    glCategories: GLCategory[];
    totalCount: number;
    currentPage: number;
    pageSize: number;
    setPage: (page: number) => void;
    getInvoice: (id: string) => Invoice | undefined;
    updateInvoice: (id: string, data: Partial<Invoice>) => Promise<void>;
    uploadInvoice: (file: File) => Promise<void>;
    deleteInvoice: (id: string) => void;
    refreshInvoices: (skip?: number, limit?: number, search?: string, status?: string) => Promise<void>;
    refreshStats: () => Promise<void>;
    fetchGLCategories: () => Promise<void>;
    createGLCategory: (category: Omit<GLCategory, 'id'>) => Promise<void>;
    updateGLCategory: (id: string, category: Omit<GLCategory, 'id'>) => Promise<void>;
    deleteGLCategory: (id: string) => Promise<void>;
    getSKUCategory: (sku: string) => Promise<string | null>;
    isLoading: boolean;
}

const InvoiceContext = createContext<InvoiceContextType | undefined>(undefined);

const API_BASE = import.meta.env.VITE_API_BASE ||
    (import.meta.env.PROD ? 'https://invoice-backend-a1gb.onrender.com' : 'http://localhost:8000');
const API_URL = `${API_BASE}/api`;

export const InvoiceProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
    const { getToken, orgId, user, disableAuth } = useAuth();
    const [invoices, setInvoices] = useState<Invoice[]>([]);
    const [glCategories, setGlCategories] = useState<GLCategory[]>([]);
    const [isLoading, setIsLoading] = useState(true);
    const [stats, setStats] = useState<DashboardStats>({
        totalInvoices: 0,
        needsReview: 0,
        approved: 0,
        issueCount: 0,
        timeSaved: '0h'
    });
    const [totalCount, setTotalCount] = useState(0);
    const [currentPage, setCurrentPage] = useState(1);
    const [pageSize, setPageSize] = useState(25);
    const [lastFilters, setLastFilters] = useState({ search: "", status: "all" });

    const refreshStats = useCallback(async () => {
        try {
            const token = await getToken();
            if (!token && !disableAuth) return;
            const response = await fetch(`${API_URL}/invoices/stats`, {
                headers: {
                    ...(token ? { Authorization: `Bearer ${token}` } : {}),
                    ...(orgId ? { "x-organization-id": orgId } : {})
                }
            });
            if (response.ok) {
                const data = await response.json();
                setStats(data);
            }
        } catch (error) {
            console.error("Failed to fetch stats", error);
        }
    }, [getToken, disableAuth, orgId]);

    const [retryCount, setRetryCount] = useState(0);

    const refreshInvoices = useCallback(async (skip = 0, limit = 25, search = "", status = "all") => {
        // Prevent infinite loops if we've failed too many times
        if (retryCount > 3) {
            console.error("DEBUG: Max retries reached for fetching invoices. Stopping.");
            if (retryCount === 4) {
                toast.error("Unable to connect to server. Please refresh the page manually.");
                setRetryCount(5);
            }
            return;
        }

        setIsLoading(true);
        setLastFilters({ search, status });

        // Also refresh stats whenever we refresh invoices to keep counts in sync
        refreshStats();

        const queryParams = new URLSearchParams({
            skip: skip.toString(),
            limit: limit.toString(),
        });
        if (search) queryParams.append('search', search);
        if (status && status !== 'all') queryParams.append('status', status);

        const url = `${API_URL}/invoices?${queryParams.toString()}`;

        try {
            const token = await getToken();

            console.log(`[InvoiceDebug] Fetching invoices from ${url}`);
            console.log(`[InvoiceDebug] Auth State - Token present: ${!!token}, OrgID: ${orgId}, DisableAuth: ${disableAuth}`);

            if (!token && !disableAuth) {
                console.warn("[InvoiceDebug] Aborting fetch: No token and auth is enabled.");
                setIsLoading(false);
                return;
            }

            const response = await fetch(url, {
                headers: {
                    ...(token ? { Authorization: `Bearer ${token}` } : {}),
                    ...(orgId ? { "x-organization-id": orgId } : {})
                }
            });

            if (response.ok) {
                const data = await response.json();
                console.log("[InvoiceDebug] Fetched invoices successfully. Count:", Array.isArray(data) ? data.length : data.items?.length);

                setRetryCount(0);

                if (Array.isArray(data)) {
                    setInvoices(data);
                    setTotalCount(data.length);
                    setCurrentPage(1);
                } else {
                    setInvoices(data.items || []);
                    setTotalCount(data.total || 0);
                    setPageSize(data.limit || 25);
                    setCurrentPage(Math.floor((data.skip || 0) / (data.limit || 25)) + 1);
                }
            } else {
                console.error(`[InvoiceDebug] Failed to fetch invoices. Status: ${response.status}`);
                if (response.status === 401) {
                    console.error("[InvoiceDebug] 401 Unauthorized - Token might be invalid or expired.");
                }
                if (response.status >= 500) {
                    setRetryCount(prev => prev + 1);
                }
            }
        } catch (error) {
            console.error(`[InvoiceDebug] Network or Fetch error:`, error);
            setRetryCount(prev => prev + 1);
        } finally {
            setIsLoading(false);
        }
    }, [getToken, disableAuth, retryCount, refreshStats, orgId]);

    const setPage = useCallback((page: number) => {
        const skip = (page - 1) * pageSize;
        refreshInvoices(skip, pageSize, lastFilters.search, lastFilters.status);
    }, [pageSize, refreshInvoices, lastFilters]);

    const fetchGLCategories = useCallback(async () => {
        try {
            const token = await getToken();
            if (!token && !disableAuth) return;
            const response = await fetch(`${API_URL}/gl-categories`, {
                headers: {
                    ...(token ? { Authorization: `Bearer ${token}` } : {}),
                    ...(orgId ? { "x-organization-id": orgId } : {})
                }
            });
            if (response.ok) {
                const data = await response.json();
                setGlCategories(data);
            }
        } catch (error) {
            console.error("Failed to fetch GL categories", error);
        }
    }, [getToken, disableAuth, orgId]);

    useEffect(() => {
        // Optimization: Skip fetching data if we are in the standalone PDF view
        // The PDF view receives its data via URL parameters to be instant
        if (window.location.pathname.endsWith('/pdf')) {
            setIsLoading(false);
            return;
        }

        if (user || orgId || disableAuth) {
            refreshInvoices();
            fetchGLCategories();
        }
    }, [user, orgId, disableAuth, refreshInvoices, fetchGLCategories]);

    // Stats are now fetched globally from the backend, so we don't need to recalculate them here
    // based on the current page's invoices.

    const getInvoice = useCallback((id: string) => invoices.find(i => i.id === id), [invoices]);

    const updateInvoice = useCallback(async (id: string, data: Partial<Invoice>) => {
        // Optimistic Update: Snapshot current state for rollback
        const previousInvoices = [...invoices];

        // Apply update immediately
        setInvoices(prev => prev.map(inv =>
            inv.id === id ? { ...inv, ...data } : inv
        ));

        try {
            const token = await getToken();
            const response = await fetch(`${API_URL}/invoices/${id}`, {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json',
                    ...(token ? { Authorization: `Bearer ${token}` } : {}),
                    ...(orgId ? { "x-organization-id": orgId } : {})
                },
                body: JSON.stringify(data),
            });

            if (response.ok) {
                const updated = await response.json();
                // Confirm update with server data (important for calculated fields)
                setInvoices(prev => prev.map(inv => inv.id === id ? updated : inv));

                // Send Feedback (Fire and Forget)
                fetch(`${API_URL}/invoices/${id}/feedback`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        Authorization: `Bearer ${token}`
                    },
                    body: JSON.stringify(data),
                }).catch(err => console.error("Feedback failed", err));

            } else {
                // Revert on failure
                console.error("Update failed, reverting optimistic change");
                setInvoices(previousInvoices);
                toast.error("Failed to update invoice");
            }
        } catch (error) {
            // Revert on error
            console.error("Network error, reverting optimistic change", error);
            setInvoices(previousInvoices);
            toast.error("Network error updating invoice");
        }
    }, [invoices, getToken, orgId]);

    const uploadInvoice = async (file: File) => {
        const formData = new FormData();
        formData.append('file', file);

        try {
            const token = await getToken();
            const response = await fetch(`${API_URL}/invoices/upload`, {
                method: 'POST',
                headers: { ...(token ? { Authorization: `Bearer ${token}` } : {}) },
                body: formData,
            });

            if (response.ok) {
                const newInvoices: Invoice[] = await response.json();
                console.log("DEBUG: Upload success. New Invoices:", newInvoices);
                setInvoices(prev => [...newInvoices, ...prev]);
                setTotalCount(prev => prev + newInvoices.length);
                toast.success(`Uploaded and processed ${newInvoices.length} invoice(s)!`);
            } else {
                console.error("DEBUG: Upload failed. Status:", response.status);
                toast.error("Upload failed");
            }
        } catch (error) {
            console.error(error);
            toast.error("Network error uploading invoice");
        }
    };

    const deleteInvoice = async (id: string) => {
        try {
            const token = await getToken();
            const response = await fetch(`${API_URL}/invoices/${id}`, {
                method: 'DELETE',
                headers: {
                    ...(token ? { Authorization: `Bearer ${token}` } : {}),
                    ...(orgId ? { "x-organization-id": orgId } : {})
                },
            });

            if (response.ok) {
                setInvoices(prev => prev.filter(i => i.id !== id));
                setTotalCount(prev => prev - 1);
                toast.success("Invoice deleted");
            } else {
                toast.error("Failed to delete invoice");
            }
        } catch (error) {
            console.error(error);
            toast.error("Network error deleting invoice");
        }
    };

    const createGLCategory = async (category: Omit<GLCategory, 'id'>) => {
        try {
            const token = await getToken();
            const response = await fetch(`${API_URL}/gl-categories`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    ...(token ? { Authorization: `Bearer ${token}` } : {}),
                    ...(orgId ? { "x-organization-id": orgId } : {})
                },
                body: JSON.stringify(category),
            });
            if (response.ok) {
                const newCategory = await response.json();
                setGlCategories(prev => [...prev, newCategory]);
                toast.success("Category created");
            }
        } catch (error) {
            console.error(error);
            toast.error("Failed to create category");
        }
    };

    const updateGLCategory = async (id: string, category: Omit<GLCategory, 'id'>) => {
        try {
            const token = await getToken();
            const response = await fetch(`${API_URL}/gl-categories/${id}`, {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json',
                    ...(token ? { Authorization: `Bearer ${token}` } : {}),
                    ...(orgId ? { "x-organization-id": orgId } : {})
                },
                body: JSON.stringify(category),
            });
            if (response.ok) {
                const updated = await response.json();
                setGlCategories(prev => prev.map(c => c.id === id ? updated : c));
                toast.success("Category updated");
            }
        } catch (error) {
            console.error(error);
            toast.error("Failed to update category");
        }
    };

    const deleteGLCategory = async (id: string) => {
        try {
            const token = await getToken();
            const response = await fetch(`${API_URL}/gl-categories/${id}`, {
                method: 'DELETE',
                headers: {
                    ...(token ? { Authorization: `Bearer ${token}` } : {}),
                    ...(orgId ? { "x-organization-id": orgId } : {})
                },
            });
            if (response.ok) {
                setGlCategories(prev => prev.filter(c => c.id !== id));
                toast.success("Category deleted");
            }
        } catch (error) {
            console.error(error);
            toast.error("Failed to delete category");
        }
    };

    const getSKUCategory = async (sku: string): Promise<string | null> => {
        try {
            const token = await getToken();
            const response = await fetch(`${API_URL}/sku-mappings/${sku}`, {
                headers: {
                    ...(token ? { Authorization: `Bearer ${token}` } : {}),
                    ...(orgId ? { "x-organization-id": orgId } : {})
                }
            });
            if (response.ok) {
                const data = await response.json();
                return data.category_gl_code;
            }
        } catch (error) {
            console.error(error);
        }
        return null;
    };

    return (
        <InvoiceContext.Provider value={{
            invoices,
            stats,
            glCategories,
            totalCount,
            currentPage,
            pageSize,
            setPage,
            getInvoice,
            updateInvoice,
            uploadInvoice,
            deleteInvoice,
            refreshInvoices,
            refreshStats,
            fetchGLCategories,
            createGLCategory,
            updateGLCategory,
            deleteGLCategory,
            getSKUCategory,
            isLoading
        }}>
            {children}
        </InvoiceContext.Provider>
    );
};

export const useInvoice = () => {
    const context = useContext(InvoiceContext);
    if (context === undefined) {
        throw new Error('useInvoice must be used within an InvoiceProvider');
    }
    return context;
};
