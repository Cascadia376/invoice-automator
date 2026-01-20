import { useInvoice } from "@/context/InvoiceContext";
import { useAuth } from "@/context/AuthContext";
import { useNavigate } from "react-router-dom";
import React, { useState, useEffect } from "react";
import { toast } from "sonner";
import { Search, Plus, Inbox, Beaker, MoreVertical, AlertCircle, Clock, FileText, FileDown, Trash2, CheckCircle } from "lucide-react";
import { formatCurrency } from "@/lib/utils";

export default function Dashboard() {
    const {
        invoices, refreshInvoices, totalCount, currentPage, pageSize, setPage, deleteInvoice, updateInvoice, stats
    } = useInvoice();
    const { getToken } = useAuth();
    const navigate = useNavigate();
    const [searchTerm, setSearchTerm] = useState("");
    const [statusFilter, setStatusFilter] = useState<'all' | 'needs_review' | 'approved' | 'failed' | 'issue'>('all');
    const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
    const [isLoading, setIsLoading] = useState(false);

    // Debounced search effect
    useEffect(() => {
        const timer = setTimeout(() => {
            refreshInvoices(0, pageSize, searchTerm, statusFilter);
        }, 300);
        return () => clearTimeout(timer);
    }, [searchTerm, statusFilter, refreshInvoices, pageSize]);

    // Use current invoices directly as they are already filtered by the server
    const filteredInvoices = invoices;

    // Calculate dynamic stats from actual invoices
    const totalOverdue = invoices
        .filter(i => {
            // Simple overdue logic: if status is needs_review and date is older than 30 days
            // For now, we'll just mock it or assume 'failed' is overdue for this demo, 
            // or add a real due date check if we have it later.
            return false;
        })
        .reduce((sum, i) => sum + i.totalAmount, 0);

    const pendingAmount = invoices
        .filter(i => i.status === 'needs_review')
        .reduce((sum, i) => sum + i.totalAmount, 0);

    const approvedAmount = stats.approved; // Note: We might want currency stats too later
    const issueAmount = stats.issueCount;

    const maxAmount = Math.max(pendingAmount, approvedAmount, issueAmount, 1); // Avoid div by 0

    const toggleSelectAll = () => {
        if (selectedIds.size === filteredInvoices.length) {
            setSelectedIds(new Set());
        } else {
            setSelectedIds(new Set(filteredInvoices.map(i => i.id)));
        }
    };

    const toggleSelect = (id: string) => {
        const newSelected = new Set(selectedIds);
        if (newSelected.has(id)) {
            newSelected.delete(id);
        } else {
            newSelected.add(id);
        }
        setSelectedIds(newSelected);
    };

    const handleBulkDelete = async () => {
        if (!confirm(`Are you sure you want to delete ${selectedIds.size} invoices?`)) return;

        for (const id of selectedIds) {
            await deleteInvoice(id);
        }
        setSelectedIds(new Set());
        toast.success("Invoices deleted");
    };

    const handleBulkApprove = async () => {
        for (const id of selectedIds) {
            await updateInvoice(id, { status: 'approved' });
        }
        setSelectedIds(new Set());
        toast.success("Invoices approved");
    };

    const handleBulkReject = async () => {
        for (const id of selectedIds) {
            await updateInvoice(id, { status: 'failed' });
        }
        setSelectedIds(new Set());
        toast.success("Invoices rejected");
    };

    const handleBulkPostToPos = async () => {
        const ids = Array.from(selectedIds);
        const approvedIds = invoices
            .filter(i => ids.includes(i.id) && i.status === 'approved')
            .map(i => i.id);

        if (approvedIds.length === 0) {
            toast.error("Only approved invoices can be posted to POS");
            return;
        }

        if (approvedIds.length < ids.length) {
            if (!confirm(`${ids.length - approvedIds.length} selected invoices are not approved and will be skipped. Continue?`)) return;
        }

        setIsLoading(true);
        try {
            const token = await getToken();
            const API_BASE = import.meta.env.PROD ? 'https://invoice-backend-a1gb.onrender.com' : 'http://localhost:8000';
            const response = await fetch(`${API_BASE}/api/invoices/bulk-post`, {
                method: "PATCH",
                headers: {
                    "Content-Type": "application/json",
                    "Authorization": `Bearer ${token}`
                },
                body: JSON.stringify(approvedIds)
            });

            if (!response.ok) throw new Error("Bulk post failed");

            toast.success(`Marked ${approvedIds.length} invoices as posted`);
            setSelectedIds(new Set());
            // Refresh invoices to show updated state
            refreshInvoices(0, pageSize, searchTerm, statusFilter);
        } catch (error: any) {
            toast.error(`Post failed: ${error.message}`);
        } finally {
            setIsLoading(false);
        }
    };

    const handleLoadDemo = async () => {
        const toastId = toast.loading("Generating demo invoice...");
        try {
            const token = await getToken();
            const API_BASE = import.meta.env.VITE_API_BASE ||
                (import.meta.env.PROD ? 'https://invoice-backend-a1gb.onrender.com' : 'http://localhost:8000');
            const res = await fetch(`${API_BASE}/api/seed/demo`, {
                method: "POST",
                headers: { ...(token ? { 'Authorization': `Bearer ${token}` } : {}) }
            });
            if (!res.ok) throw new Error("Failed");
            toast.success("Demo invoice loaded! Jarvis is ready.", { id: toastId });
            setTimeout(() => window.location.reload(), 1000);
        } catch (e) {
            toast.error("Could not load demo data", { id: toastId });
        }
    };

    const handleExportCSV = () => {
        if (filteredInvoices.length === 0) {
            toast.error("No invoices to export");
            return;
        }

        const headers = ["Invoice Number", "Vendor", "Date", "Amount", "Currency", "Status", "ID"];
        const csvContent = [
            headers.join(","),
            ...filteredInvoices.map(invoice => [
                `"${invoice.invoiceNumber}"`,
                `"${invoice.vendorName}"`,
                `"${invoice.date}"`,
                invoice.totalAmount,
                "CAD",
                `"${invoice.status}"`,
                `"${invoice.id}"`
            ].join(","))
        ].join("\n");

        const blob = new Blob([csvContent], { type: "text/csv;charset=utf-8;" });
        const link = document.createElement("a");
        const url = URL.createObjectURL(blob);
        link.setAttribute("href", url);
        link.setAttribute("download", `invoices_export_${new Date().toISOString().split('T')[0]}.csv`);
        link.style.visibility = "hidden";
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        toast.success(`Exported ${filteredInvoices.length} invoices`);
    };

    const handleBulkExportExcel = async () => {
        setIsLoading(true);
        const API_BASE = import.meta.env.PROD ? 'https://invoice-backend-a1gb.onrender.com' : 'http://localhost:8000';
        try {
            const ids = Array.from(selectedIds);
            const response = await fetch(`${API_BASE}/api/invoices/export/excel/bulk`, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    "Authorization": `Bearer ${await getToken()}`
                },
                body: JSON.stringify(ids)
            });

            if (!response.ok) throw new Error("Export failed");

            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement("a");
            a.href = url;
            a.download = `Invoices_Bulk_Export_${new Date().toISOString().split('T')[0]}.zip`;
            document.body.appendChild(a);
            a.click();
            window.URL.revokeObjectURL(url);
            document.body.removeChild(a);

            toast.success("Bulk export successful", {
                description: `Exported ${ids.length} invoices to ZIP.`,
            });
        } catch (error: any) {
            toast.error("Bulk export failed", {
                description: error.message,
            });
            toast.error("Bulk export failed", {
                description: error.message,
            });
        } finally {
            setIsLoading(false);
        }
    };

    const handleBulkExportApproved = async () => {
        // Gets ALL approved invoices from the current filtered view
        const approvedInvoices = filteredInvoices.filter(i => i.status === 'approved');

        if (approvedInvoices.length === 0) {
            toast.error("No approved invoices found in current view");
            return;
        }

        const toastId = toast.loading(`Preparing export for ${approvedInvoices.length} invoices...`);
        setIsLoading(true);

        const API_BASE = import.meta.env.PROD ? 'https://invoice-backend-a1gb.onrender.com' : 'http://localhost:8000';

        try {
            const ids = approvedInvoices.map(i => i.id);
            const token = await getToken();

            const response = await fetch(`${API_BASE}/api/invoices/export/excel/bulk-approved`, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    "Authorization": `Bearer ${token}`
                },
                body: JSON.stringify(ids)
            });

            if (!response.ok) {
                const err = await response.json();
                throw new Error(err.detail || "Export failed");
            }

            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement("a");
            a.href = url;
            a.download = `Approved_Invoices_${new Date().toISOString().split('T')[0]}.zip`;
            document.body.appendChild(a);
            a.click();
            window.URL.revokeObjectURL(url);
            document.body.removeChild(a);

            toast.success("Export successful", { id: toastId });
        } catch (error: any) {
            console.error(error);
            toast.error("Export failed", {
                id: toastId,
                description: error.message
            });
        } finally {
            setIsLoading(false);
        }
    };

    return (
        <div className="space-y-6">

            <div className="flex flex-wrap justify-between items-center gap-4">
                <p className="text-3xl font-black leading-tight tracking-[-0.033em] text-gray-900">Invoices</p>
                <div className="flex gap-2">
                    {selectedIds.size > 0 && (
                        <div className="flex gap-2 animate-in fade-in slide-in-from-top-2 bg-white p-1 rounded-lg border border-gray-200 shadow-sm mr-2">
                            <button onClick={handleBulkExportExcel} className="flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium text-white bg-blue-600 rounded-md hover:bg-blue-700 transition-colors">
                                <FileDown className="h-4 w-4" />
                                Export Excel ({selectedIds.size})
                            </button>
                            <button onClick={handleBulkPostToPos} disabled={isLoading} className="flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium text-white bg-indigo-600 rounded-md hover:bg-indigo-700 transition-colors disabled:opacity-50">
                                <CheckCircle className="h-4 w-4" />
                                Post to POS ({selectedIds.size})
                            </button>
                            <button onClick={handleBulkApprove} className="px-3 py-1.5 text-sm font-medium text-white bg-green-600 rounded-md hover:bg-green-700 transition-colors">
                                Approve ({selectedIds.size})
                            </button>
                            <button onClick={handleBulkReject} className="px-3 py-1.5 text-sm font-medium text-white bg-red-600 rounded-md hover:bg-red-700 transition-colors">
                                Reject ({selectedIds.size})
                            </button>
                            <button onClick={handleBulkDelete} className="px-3 py-1.5 text-sm font-medium text-gray-700 bg-gray-100 rounded-md hover:bg-gray-200 transition-colors">
                                Delete ({selectedIds.size})
                            </button>
                        </div>
                    )}

                    <button
                        onClick={handleBulkExportApproved}
                        disabled={isLoading}
                        className="inline-flex items-center gap-2 px-4 py-2 text-sm font-medium text-white bg-green-600 border border-transparent rounded-lg hover:bg-green-700 transition-colors shadow-sm disabled:opacity-50"
                    >
                        <FileDown className="h-4 w-4" />
                        Download Approved (XLSX)
                    </button>

                    <button
                        onClick={handleExportCSV}
                        className="inline-flex items-center gap-2 px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors shadow-sm"
                    >
                        <FileText className="h-4 w-4" />
                        Export List CSV
                    </button>
                </div>
            </div>

            <div className="mb-8 grid grid-cols-1 gap-6 lg:grid-cols-4">
                <div
                    onClick={() => {
                        navigate("/issues");
                    }}
                    className="cursor-pointer rounded-xl border border-gray-200 bg-white p-6 shadow-sm transition-all hover:shadow-md hover:border-red-200"
                >
                    <div className="flex items-center justify-between">
                        <div>
                            <p className="text-sm font-medium text-gray-500">Issue Tracker</p>
                            <p className="mt-2 text-3xl font-bold text-gray-900">
                                {stats.issueCount}
                            </p>
                        </div>
                        <div className="rounded-full bg-red-50 p-3">
                            <AlertCircle className="h-6 w-6 text-red-500" />
                        </div>
                    </div>
                    <div className="mt-4 flex items-center text-sm text-red-600">
                        <span className="font-medium">
                            {stats.issueCount} items
                        </span>
                        <span className="ml-2 text-gray-400">• Needs resolution</span>
                    </div>
                </div>

                <div
                    onClick={() => setStatusFilter('needs_review')}
                    className={`cursor-pointer rounded-xl border bg-white p-6 shadow-sm transition-all hover:shadow-md ${statusFilter === 'needs_review' ? 'ring-2 ring-amber-500 ring-offset-2' : 'border-gray-200'}`}
                >
                    <div className="flex items-center justify-between">
                        <div>
                            <p className="text-sm font-medium text-gray-500">Pending Approval</p>
                            <p className="mt-2 text-3xl font-bold text-gray-900">
                                {formatCurrency(pendingAmount)}
                            </p>
                        </div>
                        <div className="rounded-full bg-amber-50 p-3">
                            <Clock className="h-6 w-6 text-amber-500" />
                        </div>
                    </div>
                    <div className="mt-4 flex items-center text-sm text-amber-600">
                        <span className="font-medium">{invoices.filter(i => i.status === 'needs_review').length} invoices</span>
                        <span className="ml-2 text-gray-400">• Action required</span>
                    </div>
                </div>

                <div
                    onClick={() => setStatusFilter('all')}
                    className="cursor-pointer rounded-xl border border-gray-200 bg-white p-6 shadow-sm transition-all hover:shadow-md"
                >
                    <div className="flex items-center justify-between">
                        <div>
                            <p className="text-sm font-medium text-gray-500">Processed (30d)</p>
                            <p className="mt-2 text-3xl font-bold text-gray-900">{stats.totalInvoices}</p>
                        </div>
                        <div className="rounded-full bg-primary/10 p-3">
                            <FileText className="h-6 w-6 text-primary" />
                        </div>
                    </div>
                    <div className="mt-4 flex items-center text-sm text-primary">
                        <span className="font-medium">+12%</span>
                        <span className="ml-2 text-gray-400">from last month</span>
                    </div>
                </div>

                <div className="rounded-xl border border-gray-200 bg-white p-6 shadow-sm">
                    <p className="mb-6 text-sm font-medium text-gray-500">Volume by Status</p>
                    <div className="flex items-end justify-between gap-4 h-16">
                        <div className="flex flex-col items-center gap-2 flex-1">
                            <div className="w-full rounded-t-md bg-green-500/10 h-full relative group">
                                <div className="absolute bottom-0 w-full rounded-t-md bg-success transition-all duration-500 group-hover:bg-green-600" style={{ height: `${(approvedAmount / maxAmount) * 100}%`, minHeight: '4px' }}></div>
                            </div>
                            <span className="text-xs font-medium text-gray-600">Approved</span>
                        </div>
                        <div className="flex flex-col items-center gap-2 flex-1">
                            <div className="w-full rounded-t-md bg-amber-500/10 h-full relative group">
                                <div className="absolute bottom-0 w-full rounded-t-md bg-warning transition-all duration-500 group-hover:bg-amber-500" style={{ height: `${(pendingAmount / maxAmount) * 100}%`, minHeight: '4px' }}></div>
                            </div>
                            <span className="text-xs font-medium text-gray-600">Pending</span>
                        </div>
                        <div className="flex flex-col items-center gap-2 flex-1">
                            <div className="w-full rounded-t-md bg-red-500/10 h-full relative group">
                                <div className="absolute bottom-0 w-full rounded-t-md bg-danger transition-all duration-500 group-hover:bg-red-600" style={{ height: `${(issueAmount / maxAmount) * 100}%`, minHeight: '4px' }}></div>
                            </div>
                            <span className="text-xs font-medium text-gray-600">Issues</span>
                        </div>
                    </div>
                </div>
            </div>

            <div className="mb-4 flex flex-col sm:flex-row sm:items-center gap-4">
                <div className="flex gap-2 p-1 bg-gray-100 rounded-lg self-start">
                    <button
                        onClick={() => setStatusFilter('all')}
                        className={`px-3 py-1.5 text-sm font-medium rounded-md transition-all ${statusFilter === 'all' ? 'bg-white text-gray-900 shadow-sm' : 'text-gray-500 hover:text-gray-700'}`}
                    >
                        All
                    </button>
                    <button
                        onClick={() => setStatusFilter('needs_review')}
                        className={`px-3 py-1.5 text-sm font-medium rounded-md transition-all ${statusFilter === 'needs_review' ? 'bg-white text-warning shadow-sm' : 'text-gray-500 hover:text-gray-700'}`}
                    >
                        Pending
                    </button>
                    <button
                        onClick={() => setStatusFilter('approved')}
                        className={`px-3 py-1.5 text-sm font-medium rounded-md transition-all ${statusFilter === 'approved' ? 'bg-white text-success shadow-sm' : 'text-gray-500 hover:text-gray-700'}`}
                    >
                        Approved
                    </button>
                    <button
                        onClick={() => setStatusFilter('failed')}
                        className={`px-3 py-1.5 text-sm font-medium rounded-md transition-all ${statusFilter === 'failed' ? 'bg-white text-danger shadow-sm' : 'text-gray-500 hover:text-gray-700'}`}
                    >
                        Rejected
                    </button>
                    <button
                        onClick={() => setStatusFilter('issue')}
                        className={`px-3 py-1.5 text-sm font-medium rounded-md transition-all ${statusFilter === 'issue' ? 'bg-white text-red-600 shadow-sm' : 'text-gray-500 hover:text-gray-700'}`}
                    >
                        Issues
                    </button>
                </div>

                <div className="relative flex-grow min-w-[200px]">
                    <Search className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-gray-400 h-5 w-5" />
                    <input
                        value={searchTerm}
                        onChange={(e) => setSearchTerm(e.target.value)}
                        className="w-full rounded-lg border border-gray-300 bg-white py-2 pl-10 pr-4 text-sm text-gray-900 placeholder:text-gray-500 focus:border-primary focus:ring-primary focus:ring-1 focus:outline-none transition-shadow"
                        placeholder="Search invoices..."
                        type="text"
                    />
                </div>
                <button
                    onClick={() => navigate("/upload")}
                    className="flex-shrink-0 flex h-10 w-10 cursor-pointer items-center justify-center overflow-hidden rounded-lg bg-primary text-white hover:bg-primary/90 transition-colors shadow-sm"
                >
                    <Plus className="h-6 w-6" />
                </button>
            </div>

            <div className="overflow-hidden rounded-lg border border-gray-200 bg-white shadow-sm">
                <div className="overflow-x-auto">
                    <table className="min-w-full divide-y divide-gray-200">
                        <thead className="bg-gray-50">
                            <tr>
                                <th className="px-4 py-3" scope="col">
                                    <input
                                        className="h-4 w-4 rounded border-gray-300 text-primary focus:ring-primary"
                                        type="checkbox"
                                        checked={selectedIds.size === filteredInvoices.length && filteredInvoices.length > 0}
                                        onChange={toggleSelectAll}
                                    />
                                </th>
                                <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-gray-500" scope="col">Invoice #</th>
                                <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-gray-500" scope="col">Vendor Name</th>
                                <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-gray-500" scope="col">Amount</th>
                                <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-gray-500" scope="col">Status</th>
                                <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-gray-500" scope="col">Date</th>
                                <th className="relative px-4 py-3" scope="col"><span className="sr-only">Actions</span></th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-gray-200 bg-white">
                            {filteredInvoices.length === 0 ? (
                                <tr>
                                    <td colSpan={7} className="px-4 py-16 text-center text-gray-500">
                                        <div className="flex flex-col items-center justify-center gap-4">
                                            <div className="rounded-full bg-gray-50 p-6">
                                                <Inbox className="h-12 w-12 text-gray-300" />
                                            </div>
                                            <div>
                                                <p className="text-lg font-medium text-gray-900">No invoices found</p>
                                                <p className="text-sm text-gray-500">
                                                    {searchTerm || statusFilter !== 'all' ? "Try adjusting your filters" : "Upload a PDF or try our demo data"}
                                                </p>
                                            </div>
                                            {!searchTerm && statusFilter === 'all' && (
                                                <button
                                                    onClick={handleLoadDemo}
                                                    className="mt-2 inline-flex items-center gap-2 rounded-lg bg-primary px-4 py-2 text-sm font-semibold text-white shadow-sm hover:bg-primary/90 transition-all font-sans"
                                                >
                                                    <Beaker className="h-4 w-4" />
                                                    Load Demo Data
                                                </button>
                                            )}
                                        </div>
                                    </td>
                                </tr>
                            ) : (
                                filteredInvoices.map((invoice) => (
                                    <tr
                                        key={invoice.id}
                                        className="hover:bg-gray-50 cursor-pointer transition-colors"
                                        onClick={() => navigate(`/invoices/${invoice.id}`)}
                                    >
                                        <td className="whitespace-nowrap px-4 py-3" onClick={(e) => e.stopPropagation()}>
                                            <input
                                                className="h-4 w-4 rounded border-gray-300 text-primary focus:ring-primary"
                                                type="checkbox"
                                                checked={selectedIds.has(invoice.id)}
                                                onChange={() => toggleSelect(invoice.id)}
                                            />
                                        </td>
                                        <td className="whitespace-nowrap px-4 py-3 text-sm font-medium text-gray-900">{invoice.invoiceNumber}</td>
                                        <td className="whitespace-nowrap px-4 py-3 text-sm text-gray-600">{invoice.vendorName}</td>
                                        <td className="whitespace-nowrap px-4 py-3 text-sm text-gray-900 font-medium">
                                            {formatCurrency(invoice.totalAmount)}
                                        </td>
                                        <td className="whitespace-nowrap px-4 py-3 text-sm">
                                            {invoice.status === 'needs_review' && (
                                                <span className="inline-flex items-center rounded-full bg-yellow-100 px-2.5 py-0.5 text-xs font-medium text-yellow-800">
                                                    <span className="mr-1.5 h-1.5 w-1.5 rounded-full bg-yellow-500"></span>Pending
                                                </span>
                                            )}
                                            {invoice.status === 'approved' && (
                                                <span className="inline-flex items-center rounded-full bg-green-100 px-2.5 py-0.5 text-xs font-medium text-green-800">
                                                    <span className="mr-1.5 h-1.5 w-1.5 rounded-full bg-green-500"></span>Approved
                                                </span>
                                            )}
                                            {invoice.status === 'failed' && (
                                                <span className="inline-flex items-center rounded-full bg-red-100 px-2.5 py-0.5 text-xs font-medium text-red-800">
                                                    <span className="mr-1.5 h-1.5 w-1.5 rounded-full bg-red-500"></span>Rejected
                                                </span>
                                            )}
                                            {invoice.issues && invoice.issues.length > 0 && (
                                                <span className="ml-2 inline-flex items-center rounded-full bg-orange-100 px-2.5 py-0.5 text-xs font-medium text-orange-800 border border-orange-200">
                                                    {invoice.issues.length} Issue{invoice.issues.length > 1 ? 's' : ''}
                                                </span>
                                            )}
                                        </td>
                                        <td className="whitespace-nowrap px-4 py-3 text-sm text-gray-500">{invoice.date}</td>
                                        <td className="whitespace-nowrap px-4 py-3 text-right text-sm font-medium">
                                            <button className="text-gray-400 hover:text-gray-600 transition-colors p-1 rounded-full hover:bg-gray-100">
                                                <MoreVertical className="h-4 w-4" />
                                            </button>
                                        </td>
                                    </tr>
                                ))
                            )}
                        </tbody>
                    </table>
                </div>

                {/* Pagination Controls */}
                <div className="flex items-center justify-between border-t border-gray-200 bg-white px-4 py-3 sm:px-6">
                    <div className="flex flex-1 justify-between sm:hidden">
                        <button
                            onClick={() => setPage(currentPage - 1)}
                            disabled={currentPage === 1}
                            className={`relative inline-flex items-center rounded-md border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 ${currentPage === 1 ? 'opacity-50 cursor-not-allowed' : ''}`}
                        >
                            Previous
                        </button>
                        <button
                            onClick={() => setPage(currentPage + 1)}
                            disabled={currentPage * pageSize >= totalCount}
                            className={`relative ml-3 inline-flex items-center rounded-md border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 ${currentPage * pageSize >= totalCount ? 'opacity-50 cursor-not-allowed' : ''}`}
                        >
                            Next
                        </button>
                    </div>
                    <div className="hidden sm:flex sm:flex-1 sm:items-center sm:justify-between">
                        <div>
                            <p className="text-sm text-gray-700">
                                Showing <span className="font-medium">{totalCount === 0 ? 0 : (currentPage - 1) * pageSize + 1}</span> to <span className="font-medium">{Math.min(currentPage * pageSize, totalCount)}</span> of{' '}
                                <span className="font-medium">{totalCount}</span> results
                            </p>
                        </div>
                        <div className="flex items-center gap-2">
                            <span className="text-sm text-gray-500">Page {currentPage} of {Math.ceil(totalCount / pageSize) || 1}</span>
                            <nav className="isolate inline-flex -space-x-px rounded-md shadow-sm" aria-label="Pagination">
                                <button
                                    onClick={() => setPage(currentPage - 1)}
                                    disabled={currentPage === 1}
                                    className={`relative inline-flex items-center rounded-l-md px-3 py-2 text-gray-600 ring-1 ring-inset ring-gray-300 hover:bg-gray-50 focus:z-20 focus:outline-offset-0 ${currentPage === 1 ? 'opacity-50 cursor-not-allowed' : ''}`}
                                >
                                    Previous
                                </button>
                                <button
                                    onClick={() => setPage(currentPage + 1)}
                                    disabled={currentPage * pageSize >= totalCount}
                                    className={`relative inline-flex items-center rounded-r-md px-3 py-2 text-gray-600 ring-1 ring-inset ring-gray-300 hover:bg-gray-50 focus:z-20 focus:outline-offset-0 ${currentPage * pageSize >= totalCount ? 'opacity-50 cursor-not-allowed' : ''}`}
                                >
                                    Next
                                </button>
                            </nav>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
}
