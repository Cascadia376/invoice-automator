import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { ArrowLeft, FileText, AlertTriangle, CheckCircle } from 'lucide-react';
import { Vendor, VendorCorrection } from '@/types/vendor';
import { useAuth } from '@/context/AuthContext';

const API_BASE = import.meta.env.PROD
    ? 'https://invoice-backend-a1gb.onrender.com'
    : 'http://localhost:8000';

export default function VendorDetail() {
    const { vendorId } = useParams();
    const navigate = useNavigate();
    const { getToken } = useAuth();
    const [vendor, setVendor] = useState<Vendor | null>(null);
    const [corrections, setCorrections] = useState<VendorCorrection[]>([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        if (vendorId) {
            fetchVendor();
            fetchCorrections();
        }
    }, [vendorId]);

    const fetchVendor = async () => {
        try {
            const token = await getToken();
            const response = await fetch(`${API_BASE}/api/vendors/${vendorId}`, {
                headers: { ...(token ? { Authorization: `Bearer ${token}` } : {}) }
            });

            if (response.ok) {
                const data = await response.json();
                setVendor(data);
            }
        } catch (error) {
            console.error('Failed to fetch vendor:', error);
        } finally {
            setLoading(false);
        }
    };

    const fetchCorrections = async () => {
        try {
            const token = await getToken();
            const response = await fetch(`${API_BASE}/api/vendors/${vendorId}/corrections`, {
                headers: { ...(token ? { Authorization: `Bearer ${token}` } : {}) }
            });

            if (response.ok) {
                const data = await response.json();
                setCorrections(data);
            }
        } catch (error) {
            console.error('Failed to fetch corrections:', error);
        }
    };

    if (loading) {
        return <div className="p-6">Loading...</div>;
    }

    if (!vendor) {
        return <div className="p-6">Vendor not found</div>;
    }

    return (
        <div className="p-6 space-y-6">
            {/* Header */}
            <div className="flex items-center gap-4">
                <Button variant="ghost" size="icon" onClick={() => navigate('/vendors')}>
                    <ArrowLeft className="w-4 h-4" />
                </Button>
                <div className="flex-1">
                    <h1 className="text-3xl font-bold">{vendor.name}</h1>
                    <p className="text-muted-foreground mt-1">
                        {vendor.invoiceCount || 0} invoices · {((vendor.accuracyRate || 0) * 100).toFixed(0)}% accuracy
                    </p>
                </div>
                <Button variant="outline">Edit Vendor</Button>
            </div>

            {/* Stats Cards */}
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                <Card>
                    <CardHeader className="pb-2">
                        <CardTitle className="text-sm font-medium">Total Invoices</CardTitle>
                    </CardHeader>
                    <CardContent>
                        <div className="text-2xl font-bold">{vendor.invoiceCount || 0}</div>
                    </CardContent>
                </Card>

                <Card>
                    <CardHeader className="pb-2">
                        <CardTitle className="text-sm font-medium">Corrections Made</CardTitle>
                    </CardHeader>
                    <CardContent>
                        <div className="text-2xl font-bold">{vendor.correctionCount || 0}</div>
                    </CardContent>
                </Card>

                <Card>
                    <CardHeader className="pb-2">
                        <CardTitle className="text-sm font-medium">Accuracy Rate</CardTitle>
                    </CardHeader>
                    <CardContent>
                        <div className="text-2xl font-bold">{((vendor.accuracyRate || 0) * 100).toFixed(1)}%</div>
                    </CardContent>
                </Card>

                <Card>
                    <CardHeader className="pb-2">
                        <CardTitle className="text-sm font-medium">Last Invoice</CardTitle>
                    </CardHeader>
                    <CardContent>
                        <div className="text-sm font-medium">
                            {vendor.lastInvoiceDate
                                ? new Date(vendor.lastInvoiceDate).toLocaleDateString()
                                : 'Never'}
                        </div>
                    </CardContent>
                </Card>
            </div>

            {/* Tabs */}
            <Tabs defaultValue="corrections" className="space-y-4">
                <TabsList>
                    <TabsTrigger value="corrections">Correction History</TabsTrigger>
                    <TabsTrigger value="details">Vendor Details</TabsTrigger>
                </TabsList>

                <TabsContent value="corrections" className="space-y-4">
                    <Card>
                        <CardHeader>
                            <CardTitle>Correction History</CardTitle>
                            <CardDescription>
                                Track what the system learned from your edits
                            </CardDescription>
                        </CardHeader>
                        <CardContent>
                            {corrections.length === 0 ? (
                                <div className="text-center py-8">
                                    <CheckCircle className="w-12 h-12 mx-auto text-green-500 mb-2" />
                                    <p className="text-muted-foreground">
                                        No corrections yet! The system is extracting data accurately.
                                    </p>
                                </div>
                            ) : (
                                <Table>
                                    <TableHeader>
                                        <TableRow>
                                            <TableHead>Field</TableHead>
                                            <TableHead>Original Value</TableHead>
                                            <TableHead>Corrected Value</TableHead>
                                            <TableHead>Type</TableHead>
                                            <TableHead>Date</TableHead>
                                        </TableRow>
                                    </TableHeader>
                                    <TableBody>
                                        {corrections.map((correction) => (
                                            <TableRow key={correction.id}>
                                                <TableCell className="font-medium">
                                                    {correction.fieldName.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}
                                                </TableCell>
                                                <TableCell className="text-muted-foreground">
                                                    {correction.originalValue || <span className="italic">empty</span>}
                                                </TableCell>
                                                <TableCell className="font-medium">
                                                    {correction.correctedValue}
                                                </TableCell>
                                                <TableCell>
                                                    <Badge variant={
                                                        correction.correctionType === 'missing' ? 'destructive' : 'secondary'
                                                    }>
                                                        {correction.correctionType}
                                                    </Badge>
                                                </TableCell>
                                                <TableCell className="text-muted-foreground">
                                                    {new Date(correction.createdAt).toLocaleDateString()}
                                                </TableCell>
                                            </TableRow>
                                        ))}
                                    </TableBody>
                                </Table>
                            )}
                        </CardContent>
                    </Card>
                </TabsContent>

                <TabsContent value="details" className="space-y-4">
                    <Card>
                        <CardHeader>
                            <CardTitle>Vendor Information</CardTitle>
                        </CardHeader>
                        <CardContent className="space-y-4">
                            <div>
                                <label className="text-sm font-medium">Name</label>
                                <p className="text-lg">{vendor.name}</p>
                            </div>

                            {vendor.aliases && vendor.aliases.length > 0 && (
                                <div>
                                    <label className="text-sm font-medium">Aliases</label>
                                    <div className="flex gap-2 mt-1">
                                        {vendor.aliases.map((alias, i) => (
                                            <Badge key={i} variant="outline">{alias}</Badge>
                                        ))}
                                    </div>
                                </div>
                            )}

                            {vendor.defaultGlCategory && (
                                <div>
                                    <label className="text-sm font-medium">Default GL Category</label>
                                    <p>{vendor.defaultGlCategory}</p>
                                </div>
                            )}

                            {vendor.notes && (
                                <div>
                                    <label className="text-sm font-medium">Notes</label>
                                    <p className="text-muted-foreground">{vendor.notes}</p>
                                </div>
                            )}

                            <div className="pt-4 border-t">
                                <p className="text-sm text-muted-foreground">
                                    Created: {new Date(vendor.createdAt).toLocaleDateString()}
                                </p>
                                <p className="text-sm text-muted-foreground">
                                    Last Updated: {new Date(vendor.updatedAt).toLocaleDateString()}
                                </p>
                            </div>
                        </CardContent>
                    </Card>
                </TabsContent>
            </Tabs>
        </div>
    );
}
