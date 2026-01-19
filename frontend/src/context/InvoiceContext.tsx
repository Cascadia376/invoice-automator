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
        pushed: 0,
        timeSaved: '0h'
    });
    const [totalCount, setTotalCount] = useState(0);
    const [currentPage, setCurrentPage] = useState(1);
    const [pageSize, setPageSize] = useState(25);
    const [lastFilters, setLastFilters] = useState({ search: "", status: "all" });

    const refreshInvoices = useCallback(async (skip = 0, limit = 25, search = "", status = "all") => {
        setIsLoading(true);
        setLastFilters({ search, status });
        const queryParams = new URLSearchParams({
            skip: skip.toString(),
            limit: limit.toString(),
        });
        if (search) queryParams.append('search', search);
        if (status && status !== 'all') queryParams.append('status', status);

        const url = `${API_URL}/invoices?${queryParams.toString()}`;
        console.log(`DEBUG: Refreshing invoices from ${url}`);
        try {
            const token = await getToken();
            if (!token && !disableAuth) {
                setIsLoading(false);
                return;
            }
            const response = await fetch(url, {
                headers: {
                    ...(token ? { Authorization: `Bearer ${token}` } : {})
                }
            });
            if (response.ok) {
                const data = await response.json();
                console.log("DEBUG: Fetched invoices:", data);

                if (Array.isArray(data)) {
                    // Backwards compatibility for old array response
                    setInvoices(data);
                    setTotalCount(data.length);
                    setCurrentPage(1);
                } else {
                    // New paginated object response
                    setInvoices(data.items || []);
                    setTotalCount(data.total || 0);
                    setPageSize(data.limit || 25);
                    setCurrentPage(Math.floor((data.skip || 0) / (data.limit || 25)) + 1);
                }
            } else {
                console.error(`DEBUG: Failed to fetch invoices. Status: ${response.status}`);
            }
        } catch (error) {
            console.error(`DEBUG: Network or Fetch error:`, error);
        } finally {
            setIsLoading(false);
        }
    }, [getToken, disableAuth]);

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
                    ...(token ? { Authorization: `Bearer ${token}` } : {})
                }
            });
            if (response.ok) {
                const data = await response.json();
                setGlCategories(data);
            }
        } catch (error) {
            console.error("Failed to fetch GL categories", error);
        }
    }, [getToken, disableAuth]);

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

    // Calculate stats whenever invoices change
    useEffect(() => {
        // Stats are a bit tricky with pagination if we only have current page's invoices
        // Ideally the backend returns global stats. For now we use the totalCount for total.
        const needsReview = invoices.filter(i => i.status === 'needs_review').length;
        const approved = invoices.filter(i => i.status === 'approved' || i.status === 'pushed').length;

        setStats(prev => ({
            ...prev,
            totalInvoices: totalCount,
            needsReview: prev.needsReview, // These should ideally come from backend stats
            pushed: approved,
            timeSaved: `${((approved * 15) / 60).toFixed(1)}h`
        }));
    }, [invoices, totalCount]);

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
                    ...(token ? { Authorization: `Bearer ${token}` } : {})
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
    }, [invoices, getToken]);

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
                headers: { ...(token ? { Authorization: `Bearer ${token}` } : {}) },
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
                    ...(token ? { Authorization: `Bearer ${token}` } : {})
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
                    ...(token ? { Authorization: `Bearer ${token}` } : {})
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
                headers: { ...(token ? { Authorization: `Bearer ${token}` } : {}) },
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
                headers: { ...(token ? { Authorization: `Bearer ${token}` } : {}) }
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
