import { useState, useMemo } from 'react';
import { useInvoice } from '@/context/InvoiceContext';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { CheckCircle2, AlertCircle, Calendar, Filter, Download } from 'lucide-react';

export default function MonthEndReconciliation() {
    const { invoices } = useInvoice();
    const [monthFilter, setMonthFilter] = useState(new Date().toISOString().slice(0, 7)); // YYYY-MM

    // Group invoices by vendor for the selected month
    const reconciliationData = useMemo(() => {
        const vendorGroups: Record<string, {
            name: string;
            count: number;
            total: number;
            issues: number;
            approved: number;
            invoices: any[];
        }> = {};

        invoices.forEach(inv => {
            if (inv.date.startsWith(monthFilter)) {
                if (!vendorGroups[inv.vendorName]) {
                    vendorGroups[inv.vendorName] = {
                        name: inv.vendorName,
                        count: 0,
                        total: 0,
                        issues: 0,
                        approved: 0,
                        invoices: []
                    };
                }
                const group = vendorGroups[inv.vendorName];
                group.count++;
                group.total += inv.totalAmount;
                if (inv.issueType) group.issues++;
                if (inv.status === 'approved' || inv.status === 'pushed') group.approved++;
                group.invoices.push(inv);
            }
        });

        return Object.values(vendorGroups).sort((a, b) => b.total - a.total);
    }, [invoices, monthFilter]);

    const totalApproved = reconciliationData.reduce((sum, v) => sum + v.approved, 0);
    const totalCount = reconciliationData.reduce((sum, v) => sum + v.count, 0);
    const totalAmount = reconciliationData.reduce((sum, v) => sum + v.total, 0);

    return (
        <div className="p-6 space-y-6">
            <div className="flex items-center justify-between">
                <div>
                    <h1 className="text-3xl font-bold">Month-End Reconciliation</h1>
                    <p className="text-muted-foreground mt-1">
                        Verify and reconcile vendor statements for the month
                    </p>
                </div>
                <div className="flex gap-2">
                    <div className="flex items-center gap-2 bg-white border rounded-lg px-3 py-1 text-sm shadow-sm font-medium">
                        <Calendar className="h-4 w-4 text-primary" />
                        <input
                            type="month"
                            value={monthFilter}
                            onChange={(e) => setMonthFilter(e.target.value)}
                            className="border-none focus:ring-0 p-0 text-gray-900"
                        />
                    </div>
                    <Button variant="outline" className="gap-2">
                        <Download className="h-4 w-4" />
                        Export Report
                    </Button>
                </div>
            </div>

            {/* Summary Cards */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                <Card className="bg-primary/5 border-primary/20">
                    <CardHeader className="pb-2">
                        <CardTitle className="text-sm font-medium text-primary">Reconciliation Progress</CardTitle>
                    </CardHeader>
                    <CardContent>
                        <div className="text-2xl font-bold text-primary">
                            {((totalApproved / (totalCount || 1)) * 100).toFixed(0)}%
                        </div>
                        <p className="text-xs text-primary/60 mt-1">
                            {totalApproved} of {totalCount} invoices approved
                        </p>
                    </CardContent>
                </Card>

                <Card>
                    <CardHeader className="pb-2">
                        <CardTitle className="text-sm font-medium">Monthly Total</CardTitle>
                    </CardHeader>
                    <CardContent>
                        <div className="text-2xl font-bold">
                            {new Intl.NumberFormat('en-CA', { style: 'currency', currency: 'CAD' }).format(totalAmount)}
                        </div>
                        <p className="text-xs text-muted-foreground mt-1">
                            {reconciliationData.length} active vendors
                        </p>
                    </CardContent>
                </Card>

                <Card>
                    <CardHeader className="pb-2">
                        <CardTitle className="text-sm font-medium text-red-600">Pending Issues</CardTitle>
                    </CardHeader>
                    <CardContent>
                        <div className="text-2xl font-bold text-red-600">
                            {reconciliationData.reduce((sum, v) => sum + v.issues, 0)}
                        </div>
                        <p className="text-xs text-red-600/60 mt-1">
                            Requires manual adjustment
                        </p>
                    </CardContent>
                </Card>
            </div>

            {/* Vendor Table */}
            <Card>
                <CardHeader>
                    <CardTitle>Vendor Activity Summary</CardTitle>
                    <CardDescription>
                        Total spending and status per vendor for {monthFilter}
                    </CardDescription>
                </CardHeader>
                <CardContent>
                    <Table>
                        <TableHeader>
                            <TableRow>
                                <TableHead>Vendor</TableHead>
                                <TableHead className="text-right">Invoices</TableHead>
                                <TableHead className="text-right">Total Amount</TableHead>
                                <TableHead>Status</TableHead>
                                <TableHead>Issues</TableHead>
                                <TableHead></TableHead>
                            </TableRow>
                        </TableHeader>
                        <TableBody>
                            {reconciliationData.length === 0 ? (
                                <TableRow>
                                    <TableCell colSpan={6} className="text-center py-8 text-muted-foreground">
                                        No invoices found for this period.
                                    </TableCell>
                                </TableRow>
                            ) : (
                                reconciliationData.map((vendor) => (
                                    <TableRow key={vendor.name}>
                                        <TableCell className="font-semibold">{vendor.name}</TableCell>
                                        <TableCell className="text-right">{vendor.count}</TableCell>
                                        <TableCell className="text-right font-medium">
                                            {new Intl.NumberFormat('en-CA', { style: 'currency', currency: 'CAD' }).format(vendor.total)}
                                        </TableCell>
                                        <TableCell>
                                            {vendor.approved === vendor.count ? (
                                                <Badge className="bg-green-100 text-green-800 border-green-200">
                                                    <CheckCircle2 className="h-3 w-3 mr-1" />
                                                    Fully Reconciled
                                                </Badge>
                                            ) : (
                                                <Badge variant="secondary">
                                                    {vendor.approved}/{vendor.count} Approved
                                                </Badge>
                                            )}
                                        </TableCell>
                                        <TableCell>
                                            {vendor.issues > 0 ? (
                                                <Badge variant="destructive" className="animate-pulse">
                                                    <AlertCircle className="h-3 w-3 mr-1" />
                                                    {vendor.issues} Issues
                                                </Badge>
                                            ) : (
                                                <span className="text-xs text-muted-foreground italic">None</span>
                                            )}
                                        </TableCell>
                                        <TableCell className="text-right">
                                            <Button variant="ghost" size="sm">View Details</Button>
                                        </TableCell>
                                    </TableRow>
                                ))
                            )}
                        </TableBody>
                    </Table>
                </CardContent>
            </Card>
        </div>
    );
}
