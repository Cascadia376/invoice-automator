import { useState, useMemo } from 'react';
import { useInvoice } from '@/context/InvoiceContext';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Calendar, FileText, ArrowRight, CheckCircle2, Download } from 'lucide-react';

const SAGE_CATEGORIES = [
    'BEER', 'WINE', 'LIQUOR', 'COOLERS', 'CIDER', 'MISC', 'MIX & CONFEC'
];

export default function APSageView() {
    const { invoices } = useInvoice();
    const [monthFilter, setMonthFilter] = useState(new Date().toISOString().slice(0, 7)); // YYYY-MM
    const [statusFilter, setStatusFilter] = useState<'all' | 'approved'>('approved');

    const filteredInvoices = useMemo(() => {
        return invoices.filter(inv => {
            const matchesMonth = inv.date?.startsWith(monthFilter);
            const matchesStatus = statusFilter === 'all' || inv.status === 'approved' || inv.status === 'pushed';
            return matchesMonth && matchesStatus;
        }).sort((a, b) => new Date(b.date).getTime() - new Date(a.date).getTime());
    }, [invoices, monthFilter, statusFilter]);

    const getCategoryTotals = (lineItems: any[]) => {
        const totals: Record<string, number> = {};
        SAGE_CATEGORIES.forEach(cat => totals[cat] = 0);

        lineItems.forEach(item => {
            const cat = (item.categoryGlCode || 'MISC').toUpperCase();
            if (SAGE_CATEGORIES.includes(cat)) {
                totals[cat] += item.amount;
            } else {
                totals['MISC'] += item.amount;
            }
        });
        return totals;
    };

    const formatCurrency = (val: number) =>
        new Intl.NumberFormat('en-CA', { style: 'currency', currency: 'CAD' }).format(val);

    return (
        <div className="p-6 space-y-6">
            <div className="flex items-center justify-between">
                <div>
                    <h1 className="text-3xl font-bold font-display text-primary">AP Sage Entry View</h1>
                    <p className="text-muted-foreground mt-1 text-sm">
                        Categorized summaries for quick data entry into Sage
                    </p>
                </div>
                <div className="flex gap-3">
                    <div className="flex items-center gap-2 bg-white border rounded-lg px-3 py-1 text-sm shadow-sm font-medium">
                        <Calendar className="h-4 w-4 text-primary" />
                        <input
                            type="month"
                            value={monthFilter}
                            onChange={(e) => setMonthFilter(e.target.value)}
                            className="border-none focus:ring-0 p-0 text-gray-900"
                        />
                    </div>
                    <select
                        value={statusFilter}
                        onChange={(e) => setStatusFilter(e.target.value as any)}
                        className="text-sm border rounded-lg px-3 py-1 bg-white shadow-sm focus:ring-2 focus:ring-primary/20 outline-none"
                    >
                        <option value="approved">Approved Only</option>
                        <option value="all">All Invoices</option>
                    </select>
                    <Button variant="outline" size="sm" className="gap-2">
                        <Download className="h-4 w-4" />
                        Export CSV
                    </Button>
                </div>
            </div>

            <Card className="border-none shadow-premium bg-white">
                <CardHeader className="border-b bg-gray-50/50">
                    <CardTitle className="text-lg">Invoice Distributions</CardTitle>
                    <CardDescription>
                        Copy these totals into Sage distribution fields
                    </CardDescription>
                </CardHeader>
                <CardContent className="p-0 overflow-x-auto">
                    <Table>
                        <TableHeader>
                            <TableRow className="bg-gray-50 hover:bg-gray-50">
                                <TableHead className="w-[120px]">Date</TableHead>
                                <TableHead className="w-[180px]">Vendor</TableHead>
                                <TableHead className="w-[120px]">Invoice #</TableHead>
                                {SAGE_CATEGORIES.map(cat => (
                                    <TableHead key={cat} className="text-right text-[10px] font-bold uppercase tracking-wider">{cat}</TableHead>
                                ))}
                                <TableHead className="text-right font-bold text-teal-700">Tax</TableHead>
                                <TableHead className="text-right font-bold text-brown-600">Deposit</TableHead>
                                <TableHead className="text-right font-bold">Total</TableHead>
                                <TableHead className="w-[50px]"></TableHead>
                            </TableRow>
                        </TableHeader>
                        <TableBody>
                            {filteredInvoices.length === 0 ? (
                                <TableRow>
                                    <TableCell colSpan={SAGE_CATEGORIES.length + 7} className="text-center py-20 text-muted-foreground">
                                        <div className="flex flex-col items-center gap-2">
                                            <FileText className="h-10 w-10 opacity-20" />
                                            <p>No invoices found matching current filters.</p>
                                        </div>
                                    </TableCell>
                                </TableRow>
                            ) : (
                                filteredInvoices.map((inv) => {
                                    const catTotals = getCategoryTotals(inv.lineItems || []);
                                    return (
                                        <TableRow key={inv.id} className="hover:bg-primary/5 transition-colors group">
                                            <TableCell className="text-sm">{inv.date}</TableCell>
                                            <TableCell className="font-semibold text-sm truncate max-w-[180px]" title={inv.vendorName}>
                                                {inv.vendorName}
                                            </TableCell>
                                            <TableCell className="font-mono text-xs">{inv.invoiceNumber}</TableCell>

                                            {SAGE_CATEGORIES.map(cat => (
                                                <TableCell key={cat} className={`text-right text-xs ${catTotals[cat] > 0 ? 'font-medium text-gray-900' : 'text-gray-300'}`}>
                                                    {catTotals[cat] > 0 ? formatCurrency(catTotals[cat]) : '—'}
                                                </TableCell>
                                            ))}

                                            <TableCell className="text-right text-xs font-medium text-teal-700">
                                                {formatCurrency(inv.taxAmount)}
                                            </TableCell>
                                            <TableCell className="text-right text-xs font-medium text-brown-600">
                                                {formatCurrency(inv.depositAmount)}
                                            </TableCell>
                                            <TableCell className="text-right text-sm font-bold bg-gray-50 group-hover:bg-transparent">
                                                {formatCurrency(inv.totalAmount)}
                                            </TableCell>
                                            <TableCell>
                                                <Badge variant={inv.status === 'pushed' ? 'default' : 'secondary'} className="text-[10px]">
                                                    {inv.status === 'pushed' ? 'Entered' : 'Pending'}
                                                </Badge>
                                            </TableCell>
                                        </TableRow>
                                    );
                                })
                            )}
                        </TableBody>
                    </Table>
                </CardContent>
            </Card>

            <div className="bg-amber-50 border border-amber-200 p-4 rounded-lg flex items-start gap-3">
                <ArrowRight className="h-5 w-5 text-amber-600 mt-0.5" />
                <div>
                    <p className="text-sm font-medium text-amber-900">AP Instruction</p>
                    <p className="text-sm text-amber-800">
                        Use this view to quickly enter invoice distributions into Sage. Ensure the "Total" in the last column matches your Sage total after entering the category-specific amounts.
                    </p>
                </div>
            </div>
        </div>
    );
}
