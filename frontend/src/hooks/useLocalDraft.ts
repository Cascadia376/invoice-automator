import { useCallback } from 'react';
import { Invoice } from '@/types/invoice';

export function useLocalDraft() {
    const saveDraft = useCallback((id: string, data: Partial<Invoice>) => {
        if (!id) return;
        try {
            localStorage.setItem(`invoice_draft_${id}`, JSON.stringify({
                data,
                timestamp: Date.now()
            }));
        } catch (e) {
            console.error("Failed to save draft", e);
        }
    }, []);

    const getDraft = useCallback((id: string) => {
        if (!id) return null;
        try {
            const saved = localStorage.getItem(`invoice_draft_${id}`);
            if (!saved) return null;
            return JSON.parse(saved);
        } catch (e) {
            console.error("Failed to get draft", e);
            return null;
        }
    }, []);

    const clearDraft = useCallback((id: string) => {
        if (!id) return;
        localStorage.removeItem(`invoice_draft_${id}`);
    }, []);

    const hasDraft = useCallback((id: string) => {
        if (!id) return false;
        return !!localStorage.getItem(`invoice_draft_${id}`);
    }, []);

    return { saveDraft, getDraft, clearDraft, hasDraft };
}
