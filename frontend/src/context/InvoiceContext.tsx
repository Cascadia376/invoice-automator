import React, { createContext, useContext, useState, useEffect } from 'react';
import { useAuth } from "@clerk/clerk-react";
import { Invoice, DashboardStats, GLCategory } from '@/types/invoice';
import { toast } from 'sonner';

interface InvoiceContextType {
    invoices: Invoice[];
    stats: DashboardStats;
    glCategories: GLCategory[];
    getInvoice: (id: string) => Invoice | undefined;
    updateInvoice: (id: string, data: Partial<Invoice>) => Promise<void>;
    uploadInvoice: (file: File) => Promise<void>;
    pushToQBO: (id: string) => Promise<void>;
    deleteInvoice: (id: string) => void;
    refreshInvoices: () => Promise<void>;
    fetchGLCategories: () => Promise<void>;
    createGLCategory: (category: Omit<GLCategory, 'id'>) => Promise<void>;
    updateGLCategory: (id: string, category: Omit<GLCategory, 'id'>) => Promise<void>;
    deleteGLCategory: (id: string) => Promise<void>;
    getSKUCategory: (sku: string) => Promise<string | null>;
    isLoading: boolean;
}

const InvoiceContext = createContext<InvoiceContextType | undefined>(undefined);

const API_URL = '/api';

export const InvoiceProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
    const { getToken, orgId, userId } = useAuth();
    const [invoices, setInvoices] = useState<Invoice[]>([]);
    const [glCategories, setGlCategories] = useState<GLCategory[]>([]);
    const [isLoading, setIsLoading] = useState(true);
    const [stats, setStats] = useState<DashboardStats>({
        totalInvoices: 0,
        needsReview: 0,
        pushed: 0,
        timeSaved: '0h'
    });

    const refreshInvoices = async () => {
        setIsLoading(true);
        try {
            const token = await getToken();
            if (!token) {
                setIsLoading(false);
                return;
            }
            const response = await fetch(`${API_URL}/invoices`, {
                headers: { Authorization: `Bearer ${token}` }
            });
            if (response.ok) {
                const data = await response.json();
                console.log("DEBUG: Fetched invoices:", data);
                setInvoices(data);
            } else {
                console.error("DEBUG: Failed to fetch invoices. Status:", response.status);
            }
        } catch (error) {
            console.error("Failed to fetch invoices", error);
        } finally {
            setIsLoading(false);
        }
    };

    const fetchGLCategories = async () => {
        try {
            const token = await getToken();
            if (!token) return;
            const response = await fetch(`${API_URL}/gl-categories`, {
                headers: { Authorization: `Bearer ${token}` }
            });
            if (response.ok) {
                const data = await response.json();
                setGlCategories(data);
            }
        } catch (error) {
            console.error("Failed to fetch GL categories", error);
        }
    };

    useEffect(() => {
        if (userId || orgId) {
            refreshInvoices();
            fetchGLCategories();
        }
    }, [userId, orgId]);

    // Calculate stats whenever invoices change
    useEffect(() => {
        const needsReview = invoices.filter(i => i.status === 'needs_review').length;
        const pushed = invoices.filter(i => i.status === 'pushed').length;
        const total = invoices.length;
        // Mock calculation: 15 mins saved per pushed invoice
        const hoursSaved = ((pushed * 15) / 60).toFixed(1);

        setStats({
            totalInvoices: total,
            needsReview,
            pushed,
            timeSaved: `${hoursSaved}h`
        });
    }, [invoices]);

    const getInvoice = (id: string) => invoices.find(i => i.id === id);

    const updateInvoice = async (id: string, data: Partial<Invoice>) => {
        // Optimistic Update: Snapshot current state for rollback
        const previousInvoices = [...invoices];
        const originalInvoice = invoices.find(i => i.id === id);

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
                    Authorization: `Bearer ${token}`
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
    };

    const uploadInvoice = async (file: File) => {
        const formData = new FormData();
        formData.append('file', file);

        try {
            const token = await getToken();
            const response = await fetch(`${API_URL}/invoices/upload`, {
                method: 'POST',
                headers: { Authorization: `Bearer ${token}` },
                body: formData,
            });

            if (response.ok) {
                const newInvoice = await response.json();
                console.log("DEBUG: Upload success. New Invoice:", newInvoice);
                setInvoices(prev => [newInvoice, ...prev]);
                toast.success("Invoice uploaded and parsed!");
            } else {
                console.error("DEBUG: Upload failed. Status:", response.status);
                toast.error("Upload failed");
            }
        } catch (error) {
            console.error(error);
            toast.error("Network error uploading invoice");
        }
    };

    const pushToQBO = async (id: string) => {
        // Optimistic Update
        const previousInvoices = [...invoices];
        setInvoices(prev => prev.map(inv =>
            inv.id === id ? { ...inv, status: 'pushed' } : inv
        ));

        try {
            const token = await getToken();
            const response = await fetch(`${API_URL}/invoices/${id}/push`, {
                method: 'POST',
                headers: { Authorization: `Bearer ${token}` },
            });

            if (response.ok) {
                const data = await response.json();
                // Keep the 'pushed' status (or update with full server response if needed)
                toast.success(data.message || "Successfully exported to QuickBooks Online");
            } else {
                // Revert
                setInvoices(previousInvoices);
                const errorData = await response.json().catch(() => ({}));
                toast.error(errorData.detail || "Failed to export to QuickBooks");
            }
        } catch (error) {
            // Revert
            setInvoices(previousInvoices);
            console.error(error);
            toast.error("Network error exporting to QBO");
        }
    };

    const deleteInvoice = async (id: string) => {
        try {
            const token = await getToken();
            const response = await fetch(`${API_URL}/invoices/${id}`, {
                method: 'DELETE',
                headers: { Authorization: `Bearer ${token}` },
            });

            if (response.ok) {
                setInvoices(prev => prev.filter(i => i.id !== id));
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
                    Authorization: `Bearer ${token}`
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
                    Authorization: `Bearer ${token}`
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
                headers: { Authorization: `Bearer ${token}` },
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
                headers: { Authorization: `Bearer ${token}` }
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
            getInvoice,
            updateInvoice,
            uploadInvoice,
            pushToQBO,
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
