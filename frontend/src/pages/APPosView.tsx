import { useState, useEffect, useMemo } from 'react';
import { useInvoice } from '@/context/InvoiceContext';
import { useAuth } from '@/context/AuthContext';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Calendar, FileText, Download, CheckCircle, TrendingUp, DollarSign, ListFilter } from 'lucide-react';
import { formatCurrency } from '@/lib/utils';
import { toast } from 'sonner';

interface CategorySummary {
    category_totals: Record<string, number>;
    total_tax: number;
    total_deposit: number;
    total_amount: number;
    invoice_count: number;
}

export default function APPosView() {
    const { invoices, refreshInvoices } = useInvoice();
    const { getToken } = useAuth();
    const [monthFilter, setMonthFilter] = useState(new Date().toISOString().slice(0, 7)); // YYYY-MM
    const [summary, setSummary] = useState<CategorySummary | null>(null);
    const [loading, setLoading] = useState(true);

    const API_BASE = import.meta.env.PROD ? 'https://invoice-backend-a1gb.onrender.com' : 'http://localhost:8000';

    const fetchSummary = async () => {
        setLoading(true);
        try {
            const token = await getToken();
            const response = await fetch(`${API_BASE}/api/invoices/stats/category-summary?month=${monthFilter}`, {
                headers: { ...(token ? { 'Authorization': `Bearer ${token}` } : {}) }
            });
            if (response.ok) {
                const data = await response.json();
                setSummary(data);
            } else {
                toast.error("Failed to load category summary");
            }
        } catch (error) {
            console.error("Error fetching summary:", error);
            toast.error("Network error loading summary");
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchSummary();
    }, [monthFilter]);

    const postedInvoices = useMemo(() => {
        return invoices.filter(inv => {
            const matchesMonth = inv.date?.startsWith(monthFilter);
            return matchesMonth && inv.status === 'approved' && inv.isPosted;
        }).sort((a, b) => new Date(b.date).getTime() - new Date(a.date).getTime());
    }, [invoices, monthFilter]);

    return (
        <div className="p-6 space-y-8 max-w-[1600px] mx-auto">
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
                <div>
                    <h1 className="text-3xl font-bold font-display text-gray-900 tracking-tight">AP POS Summary</h1>
                    <p className="text-muted-foreground mt-1 text-sm font-medium">
                        Aggregated totals for approved invoices posted in the POS
                    </p>
                </div>
                <div className="flex items-center gap-3">
                    <div className="flex items-center gap-2 bg-white border border-gray-200 rounded-lg px-4 py-2 text-sm shadow-sm font-semibold transition-all hover:border-primary/50">
                        <Calendar className="h-4 w-4 text-primary" />
                        <input
                            type="month"
                            value={monthFilter}
                            onChange={(e) => setMonthFilter(e.target.value)}
                            className="border-none focus:ring-0 p-0 text-gray-900 bg-transparent text-sm"
                        />
                    </div>
                    <Button onClick={fetchSummary} variant="outline" size="sm" className="bg-white hover:bg-gray-50 border-gray-200">
                        Refresh
                    </Button>
                </div>
            </div>

            {/* High Level Stats */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
                <Card className="border-none shadow-premium transition-transform hover:scale-[1.02]">
                    <CardHeader className="flex flex-row items-center justify-between pb-2">
                        <CardTitle className="text-sm font-bold text-muted-foreground uppercase tracking-wider">Total Amount</CardTitle>
                        <DollarSign className="h-4 w-4 text-primary" />
                    </CardHeader>
                    <CardContent>
                        <div className="text-2xl font-bold text-gray-900">{summary ? formatCurrency(summary.total_amount) : '—'}</div>
                        <p className="text-xs text-muted-foreground mt-1">Sum of all posted invoices</p>
                    </CardContent>
                </Card>
                <Card className="border-none shadow-premium transition-transform hover:scale-[1.02]">
                    <CardHeader className="flex flex-row items-center justify-between pb-2">
                        <CardTitle className="text-sm font-bold text-muted-foreground uppercase tracking-wider">Posted Invoices</CardTitle>
                        <CheckCircle className="h-4 w-4 text-success" />
                    </CardHeader>
                    <CardContent>
                        <div className="text-2xl font-bold text-gray-900">{summary?.invoice_count || 0}</div>
                        <p className="text-xs text-muted-foreground mt-1">Processed this period</p>
                    </CardContent>
                </Card>
                <Card className="border-none shadow-premium transition-transform hover:scale-[1.02]">
                    <CardHeader className="flex flex-row items-center justify-between pb-2">
                        <CardTitle className="text-sm font-bold text-muted-foreground uppercase tracking-wider">Total Tax</CardTitle>
                        <TrendingUp className="h-4 w-4 text-blue-500" />
                    </CardHeader>
                    <CardContent>
                        <div className="text-2xl font-bold text-gray-900">{summary ? formatCurrency(summary.total_tax) : '—'}</div>
                        <p className="text-xs text-muted-foreground mt-1">Accumulated tax amount</p>
                    </CardContent>
                </Card>
                <Card className="border-none shadow-premium transition-transform hover:scale-[1.02]">
                    <CardHeader className="flex flex-row items-center justify-between pb-2">
                        <CardTitle className="text-sm font-bold text-muted-foreground uppercase tracking-wider">Total Deposits</CardTitle>
                        <ListFilter className="h-4 w-4 text-amber-500" />
                    </CardHeader>
                    <CardContent>
                        <div className="text-2xl font-bold text-gray-900">{summary ? formatCurrency(summary.total_deposit) : '—'}</div>
                        <p className="text-xs text-muted-foreground mt-1">Reusable container deposits</p>
                    </CardContent>
                </Card>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
                {/* Category Breakdown */}
                <Card className="lg:col-span-1 border-none shadow-premium h-fit">
                    <CardHeader className="border-b bg-gray-50/50">
                        <CardTitle className="text-lg flex items-center gap-2">
                            <TrendingUp className="h-5 w-5 text-primary" />
                            Category Totals
                        </CardTitle>
                        <CardDescription>Consolidated values for entry</CardDescription>
                    </CardHeader>
                    <CardContent className="p-0">
                        <Table>
                            <TableHeader>
                                <TableRow className="bg-gray-50/80">
                                    <TableHead className="font-bold">Category</TableHead>
                                    <TableHead className="text-right font-bold">Total</TableHead>
                                </TableRow>
                            </TableHeader>
                            <TableBody>
                                {!summary || Object.keys(summary.category_totals).length === 0 ? (
                                    <TableRow>
                                        <TableCell colSpan={2} className="text-center py-12 text-muted-foreground">
                                            No data for this period
                                        </TableCell>
                                    </TableRow>
                                ) : (
                                    Object.entries(summary.category_totals).map(([cat, total]) => (
                                        <TableRow key={cat} className="hover:bg-primary/5">
                                            <TableCell className="font-medium text-sm">{cat}</TableCell>
                                            <TableCell className="text-right font-mono font-semibold text-gray-900">
                                                {formatCurrency(total)}
                                            </TableCell>
                                        </TableRow>
                                    ))
                                )}
                            </TableBody>
                        </Table>
                    </CardContent>
                </Card>

                {/* detailed List */}
                <Card className="lg:col-span-2 border-none shadow-premium overflow-hidden">
                    <CardHeader className="border-b bg-gray-50/50 flex flex-row items-center justify-between">
                        <div>
                            <CardTitle className="text-lg flex items-center gap-2">
                                <FileText className="h-5 w-5 text-primary" />
                                Posted Invoices
                            </CardTitle>
                            <CardDescription>Individual documents included in totals</CardDescription>
                        </div>
                        <Button variant="outline" size="sm" className="gap-2 bg-white">
                            <Download className="h-4 w-4" />
                            Export Details
                        </Button>
                    </CardHeader>
                    <CardContent className="p-0">
                        <Table>
                            <TableHeader>
                                <TableRow className="bg-gray-50/80">
                                    <TableHead className="w-[120px] font-bold">Date</TableHead>
                                    <TableHead className="font-bold">Vendor</TableHead>
                                    <TableHead className="font-bold">Invoice #</TableHead>
                                    <TableHead className="text-right font-bold">Tax</TableHead>
                                    <TableHead className="text-right font-bold text-gray-900">Total</TableHead>
                                </TableRow>
                            </TableHeader>
                            <TableBody>
                                {postedInvoices.length === 0 ? (
                                    <TableRow>
                                        <TableCell colSpan={5} className="text-center py-20 text-muted-foreground">
                                            <p className="mb-1">No invoices have been marked as posted for this month.</p>
                                            <p className="text-xs">Approve an invoice and click "Post to POS" to see it here.</p>
                                        </TableCell>
                                    </TableRow>
                                ) : (
                                    postedInvoices.map((inv) => (
                                        <TableRow key={inv.id} className="hover:bg-primary/5 transition-colors">
                                            <TableCell className="text-sm font-medium">{inv.date}</TableCell>
                                            <TableCell className="font-bold text-sm text-gray-900">{inv.vendorName}</TableCell>
                                            <TableCell className="font-mono text-xs text-muted-foreground">{inv.invoiceNumber}</TableCell>
                                            <TableCell className="text-right text-xs text-teal-700 font-semibold">
                                                {formatCurrency(inv.taxAmount)}
                                            </TableCell>
                                            <TableCell className="text-right text-sm font-black text-gray-900">
                                                {formatCurrency(inv.totalAmount)}
                                            </TableCell>
                                        </TableRow>
                                    ))
                                )}
                            </TableBody>
                        </Table>
                    </CardContent>
                </Card>
            </div>
        </div>
    );
}
