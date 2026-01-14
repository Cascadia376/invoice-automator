import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { useInvoice } from "@/context/InvoiceContext";
import { PDFViewer } from "@/components/invoice/PDFViewer";
import { Invoice } from "@/types/invoice";
import { Loader2 } from "lucide-react";

export default function PDFViewOnly() {
    const { id } = useParams<{ id: string }>();
    const { getInvoice, isLoading } = useInvoice();
    const [invoice, setInvoice] = useState<Invoice | undefined>(undefined);

    useEffect(() => {
        if (id) {
            const data = getInvoice(id);
            if (data) {
                setInvoice(data);
            }
        }
    }, [id, getInvoice]);

    if (isLoading || !invoice) {
        return (
            <div className="flex h-screen items-center justify-center">
                <Loader2 className="h-8 w-8 animate-spin text-primary" />
            </div>
        );
    }

    const getPdfUrl = () => {
        if (!invoice?.fileUrl) return '';
        if (invoice.fileUrl.startsWith('http')) return invoice.fileUrl;
        const API_BASE = import.meta.env.PROD ? 'https://invoice-backend-a1gb.onrender.com' : 'http://localhost:8000';
        return `${API_BASE}${invoice.fileUrl}`;
    };

    return (
        <div className="h-screen w-screen bg-gray-900 flex flex-col">
            <PDFViewer pdfUrl={getPdfUrl()} />
        </div>
    );
}
