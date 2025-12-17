import { useState, useEffect } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { Building2, Search, TrendingUp, FileText, AlertCircle } from 'lucide-react';
import { Vendor } from '@/types/vendor';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '@/context/AuthContext';

const API_BASE = import.meta.env.PROD
    ? 'https://invoice-backend-a1gb.onrender.com'
    : 'http://localhost:8000';

export default function Vendors() {
    const [vendors, setVendors] = useState<Vendor[]>([]);
    const [loading, setLoading] = useState(true);
    const [searchQuery, setSearchQuery] = useState('');
    const navigate = useNavigate();
    const { getToken } = useAuth();

    useEffect(() => {
        fetchVendors();
    }, []);

    const fetchVendors = async () => {
        try {
            const token = await getToken();
            const response = await fetch(`${API_BASE}/api/vendors`, {
                headers: { ...(token ? { Authorization: `Bearer ${token}` } : {}) }
            });

            if (response.ok) {
                const data = await response.json();
                setVendors(data);
            }
        } catch (error) {
            console.error('Failed to fetch vendors:', error);
        } finally {
            setLoading(false);
        }
    };

    const filteredVendors = vendors.filter(v =>
        v.name.toLowerCase().includes(searchQuery.toLowerCase())
    );

    const totalInvoices = vendors.reduce((sum, v) => sum + (v.invoiceCount || 0), 0);
    const avgAccuracy = vendors.length > 0
        ? vendors.reduce((sum, v) => sum + (v.accuracyRate || 0), 0) / vendors.length
        : 0;

    return (
        <div className="p-6 space-y-6">
            {/* Header */}
            <div className="flex items-center justify-between">
                <div>
                    <h1 className="text-3xl font-bold">Vendors</h1>
                    <p className="text-muted-foreground mt-1">
                        Manage vendor profiles and correction learning
                    </p>
                </div>
                <Button onClick={() => navigate('/vendors/new')}>
                    <Building2 className="w-4 h-4 mr-2" />
                    Add Vendor
                </Button>
            </div>

            {/* Stats */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <Card>
                    <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                        <CardTitle className="text-sm font-medium">Total Vendors</CardTitle>
                        <Building2 className="h-4 w-4 text-muted-foreground" />
                    </CardHeader>
                    <CardContent>
                        <div className="text-2xl font-bold">{vendors.length}</div>
                    </CardContent>
                </Card>

                <Card>
                    <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                        <CardTitle className="text-sm font-medium">Total Invoices</CardTitle>
                        <FileText className="h-4 w-4 text-muted-foreground" />
                    </CardHeader>
                    <CardContent>
                        <div className="text-2xl font-bold">{totalInvoices}</div>
                    </CardContent>
                </Card>

                <Card>
                    <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                        <CardTitle className="text-sm font-medium">Avg Accuracy</CardTitle>
                        <TrendingUp className="h-4 w-4 text-muted-foreground" />
                    </CardHeader>
                    <CardContent>
                        <div className="text-2xl font-bold">{(avgAccuracy * 100).toFixed(1)}%</div>
                    </CardContent>
                </Card>
            </div>

            {/* Search */}
            <div className="relative">
                <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-muted-foreground w-4 h-4" />
                <Input
                    placeholder="Search vendors..."
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    className="pl-10"
                />
            </div>

            {/* Vendors Table */}
            <Card>
                <CardHeader>
                    <CardTitle>Vendor List</CardTitle>
                    <CardDescription>
                        Click on a vendor to view details and correction history
                    </CardDescription>
                </CardHeader>
                <CardContent>
                    {loading ? (
                        <div className="text-center py-8 text-muted-foreground">Loading vendors...</div>
                    ) : filteredVendors.length === 0 ? (
                        <div className="text-center py-8">
                            <AlertCircle className="w-12 h-12 mx-auto text-muted-foreground mb-2" />
                            <p className="text-muted-foreground">
                                {searchQuery ? 'No vendors found' : 'No vendors yet. Upload an invoice to create one automatically.'}
                            </p>
                        </div>
                    ) : (
                        <Table>
                            <TableHeader>
                                <TableRow>
                                    <TableHead>Vendor Name</TableHead>
                                    <TableHead>Invoices</TableHead>
                                    <TableHead>Corrections</TableHead>
                                    <TableHead>Accuracy</TableHead>
                                    <TableHead>Last Invoice</TableHead>
                                    <TableHead></TableHead>
                                </TableRow>
                            </TableHeader>
                            <TableBody>
                                {filteredVendors.map((vendor) => (
                                    <TableRow
                                        key={vendor.id}
                                        className="cursor-pointer hover:bg-muted/50"
                                        onClick={() => navigate(`/vendors/${vendor.id}`)}
                                    >
                                        <TableCell className="font-medium">{vendor.name}</TableCell>
                                        <TableCell>{vendor.invoiceCount || 0}</TableCell>
                                        <TableCell>
                                            {vendor.correctionCount || 0}
                                            {(vendor.correctionCount || 0) > 0 && (
                                                <Badge variant="outline" className="ml-2">Learning</Badge>
                                            )}
                                        </TableCell>
                                        <TableCell>
                                            <Badge variant={(vendor.accuracyRate || 0) > 0.9 ? "default" : "secondary"}>
                                                {((vendor.accuracyRate || 0) * 100).toFixed(0)}%
                                            </Badge>
                                        </TableCell>
                                        <TableCell className="text-muted-foreground">
                                            {vendor.lastInvoiceDate
                                                ? new Date(vendor.lastInvoiceDate).toLocaleDateString()
                                                : 'Never'}
                                        </TableCell>
                                        <TableCell>
                                            <Button variant="ghost" size="sm">View</Button>
                                        </TableCell>
                                    </TableRow>
                                ))}
                            </TableBody>
                        </Table>
                    )}
                </CardContent>
            </Card>
        </div>
    );
}
