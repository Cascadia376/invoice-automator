import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { ArrowLeft, FileText, AlertTriangle, CheckCircle, Save, X, Edit2, Building2, AlertCircle, Search, Loader2 } from 'lucide-react';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Vendor, VendorCorrection } from '@/types/vendor';
import { useAuth } from '@/context/AuthContext';
import { toast } from '@/components/ui/use-toast';
import { GlobalVendorMapping } from '@/types/vendor';

const API_BASE = import.meta.env.VITE_API_BASE ||
    (import.meta.env.PROD ? 'https://invoice-backend-a1gb.onrender.com' : 'http://localhost:8000');

export default function VendorDetail() {
    const { vendorId } = useParams();
    const navigate = useNavigate();
    const { getToken } = useAuth();
    const [vendor, setVendor] = useState<Vendor | null>(null);
    const [corrections, setCorrections] = useState<VendorCorrection[]>([]);
    const [loading, setLoading] = useState(true);
    const [isEditing, setIsEditing] = useState(false);
    const [editedVendor, setEditedVendor] = useState<Partial<Vendor>>({});
    const [saving, setSaving] = useState(false);
    const [suggestion, setSuggestion] = useState<GlobalVendorMapping | null>(null);
    const [isSearching, setIsSearching] = useState(false);
    const [searchResults, setSearchResults] = useState<any[]>([]);
    const [searchQuery, setSearchQuery] = useState('');
    const [showResults, setShowResults] = useState(false);

    useEffect(() => {
        if (vendorId) {
            fetchVendor();
            fetchCorrections();
        }
    }, [vendorId]);

    useEffect(() => {
        if (vendor && !vendor.stellarSupplierId) {
            fetchSuggestion();
        }
    }, [vendor]);

    const fetchSuggestion = async () => {
        if (!vendor) return;
        try {
            const token = await getToken();
            const response = await fetch(`${API_BASE}/api/stellar/discover/suppliers?name=${encodeURIComponent(vendor.name)}`, {
                headers: { ...(token ? { Authorization: `Bearer ${token}` } : {}) }
            });

            if (response.ok) {
                const data = await response.json();
                setSuggestion(data);
            }
        } catch (error) {
            console.error('Failed to fetch suggestion:', error);
        }
    };

    const applySuggestion = () => {
        if (!suggestion) return;
        setEditedVendor({
            ...editedVendor,
            stellarSupplierId: suggestion.stellarSupplierId,
            stellarSupplierName: suggestion.stellarSupplierName
        });
        if (!isEditing) setIsEditing(true);
        toast({
            title: "Suggestion applied",
            description: "Review and click Save to confirm the Stellar mapping.",
        });
    };

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

    const searchStellarSuppliers = async (query: string) => {
        if (!query || query.length < 2) return;
        setIsSearching(true);
        try {
            const token = await getToken();
            const response = await fetch(`${API_BASE}/api/stellar/proxy/suppliers?name=${encodeURIComponent(query)}`, {
                headers: { ...(token ? { Authorization: `Bearer ${token}` } : {}) }
            });

            if (response.ok) {
                const data = await response.json();
                // Stellar response format based on curl: array is likely in data.items or just the response
                const items = data.items || data || [];
                setSearchResults(Array.isArray(items) ? items : []);
                setShowResults(true);
            }
        } catch (error) {
            console.error('Stellar search failed:', error);
        } finally {
            setIsSearching(false);
        }
    };

    const selectStellarSupplier = (s: any) => {
        setEditedVendor({
            ...editedVendor,
            stellarSupplierId: s.id || s.uuid,
            stellarSupplierName: s.name
        });
        setShowResults(false);
    };

    const handleEditToggle = () => {
        if (!isEditing && vendor) {
            setEditedVendor({
                name: vendor.name,
                notes: vendor.notes,
                defaultGlCategory: vendor.defaultGlCategory,
                stellarSupplierId: vendor.stellarSupplierId,
                stellarSupplierName: vendor.stellarSupplierName,
            });
        }
        setIsEditing(!isEditing);
    };

    const handleSave = async () => {
        if (!vendorId) return;
        setSaving(true);
        try {
            const token = await getToken();
            const response = await fetch(`${API_BASE}/api/vendors/${vendorId}`, {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json',
                    ...(token ? { Authorization: `Bearer ${token}` } : {})
                },
                body: JSON.stringify(editedVendor)
            });

            if (response.ok) {
                const updatedVendor = await response.json();
                setVendor(updatedVendor);
                setIsEditing(false);
                toast({
                    title: "Vendor updated",
                    description: "Vendor details have been saved successfully.",
                });
            } else {
                throw new Error('Failed to update vendor');
            }
        } catch (error) {
            console.error('Save failed:', error);
            toast({
                title: "Update failed",
                description: "There was an error saving vendor details.",
                variant: "destructive"
            });
        } finally {
            setSaving(false);
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
                {isEditing ? (
                    <div className="flex gap-2">
                        <Button variant="outline" size="sm" onClick={handleEditToggle} disabled={saving}>
                            <X className="w-4 h-4 mr-2" />
                            Cancel
                        </Button>
                        <Button size="sm" onClick={handleSave} disabled={saving}>
                            <Save className="w-4 h-4 mr-2" />
                            {saving ? "Saving..." : "Save Changes"}
                        </Button>
                    </div>
                ) : (
                    <Button variant="outline" size="sm" onClick={handleEditToggle}>
                        <Edit2 className="w-4 h-4 mr-2" />
                        Edit Vendor
                    </Button>
                )}
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
                    <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                        <div className="lg:col-span-2 space-y-6">
                            <Card>
                                <CardHeader>
                                    <div className="flex items-center justify-between">
                                        <CardTitle>Vendor Information</CardTitle>
                                    </div>
                                </CardHeader>
                                <CardContent className="space-y-4">
                                    {isEditing ? (
                                        <>
                                            <div className="space-y-2">
                                                <Label htmlFor="name">Normalized Name</Label>
                                                <Input
                                                    id="name"
                                                    value={editedVendor.name || ''}
                                                    onChange={e => setEditedVendor({ ...editedVendor, name: e.target.value })}
                                                    placeholder="Enter vendor name"
                                                />
                                            </div>
                                            <div className="space-y-2">
                                                <Label htmlFor="notes">Notes</Label>
                                                <Textarea
                                                    id="notes"
                                                    value={editedVendor.notes || ''}
                                                    onChange={e => setEditedVendor({ ...editedVendor, notes: e.target.value })}
                                                    placeholder="Add internal notes about this vendor"
                                                    rows={4}
                                                />
                                            </div>
                                        </>
                                    ) : (
                                        <>
                                            <div>
                                                <Label className="text-muted-foreground">Normalized Name</Label>
                                                <p className="text-lg font-medium">{vendor.name}</p>
                                            </div>

                                            {vendor.aliases && vendor.aliases.length > 0 && (
                                                <div>
                                                    <Label className="text-muted-foreground">Extraction Aliases</Label>
                                                    <div className="flex flex-wrap gap-2 mt-1">
                                                        {vendor.aliases.map((alias, i) => (
                                                            <Badge key={i} variant="outline">{alias}</Badge>
                                                        ))}
                                                    </div>
                                                </div>
                                            )}

                                            {vendor.defaultGlCategory && (
                                                <div>
                                                    <Label className="text-muted-foreground">Default GL Category</Label>
                                                    <p className="font-medium">{vendor.defaultGlCategory}</p>
                                                </div>
                                            )}

                                            {vendor.notes && (
                                                <div>
                                                    <Label className="text-muted-foreground">Notes</Label>
                                                    <p className="whitespace-pre-wrap">{vendor.notes}</p>
                                                </div>
                                            )}
                                        </>
                                    )}

                                    <div className="pt-4 border-t grid grid-cols-2 gap-4">
                                        <div>
                                            <p className="text-xs text-muted-foreground uppercase tracking-wider font-semibold">Created</p>
                                            <p className="text-sm">{new Date(vendor.createdAt).toLocaleDateString()}</p>
                                        </div>
                                        <div>
                                            <p className="text-xs text-muted-foreground uppercase tracking-wider font-semibold">Last Updated</p>
                                            <p className="text-sm">{new Date(vendor.updatedAt).toLocaleDateString()}</p>
                                        </div>
                                    </div>
                                </CardContent>
                            </Card>
                        </div>

                        <div className="space-y-6">
                            <Card className="border-blue-100 shadow-sm">
                                <CardHeader className="bg-blue-50/50">
                                    <div className="flex items-center gap-2">
                                        <div className="p-2 bg-blue-100 rounded-lg">
                                            <Building2 className="w-4 h-4 text-blue-600" />
                                        </div>
                                        <div>
                                            <CardTitle className="text-base text-blue-900">Stellar POS Integration</CardTitle>
                                            <CardDescription className="text-blue-700/70">Map this vendor to Stellar</CardDescription>
                                        </div>
                                    </div>
                                </CardHeader>
                                <CardContent className="pt-6 space-y-4">
                                    {isEditing ? (
                                        <>
                                            <div className="space-y-2">
                                                <Label htmlFor="stellarId" className="text-xs font-bold text-muted-foreground">STELLAR SUPPLIER ID (UUID)</Label>
                                                <div className="flex gap-2">
                                                    <Input
                                                        id="stellarId"
                                                        value={editedVendor.stellarSupplierId || ''}
                                                        onChange={e => setEditedVendor({ ...editedVendor, stellarSupplierId: e.target.value })}
                                                        placeholder="6552c5eb-..."
                                                        className="font-mono text-xs flex-1"
                                                    />
                                                </div>
                                            </div>
                                            <div className="space-y-2 relative">
                                                <Label htmlFor="stellarName" className="text-xs font-bold text-muted-foreground">STELLAR SUPPLIER NAME</Label>
                                                <div className="relative">
                                                    <Input
                                                        id="stellarName"
                                                        value={editedVendor.stellarSupplierName || ''}
                                                        onChange={e => {
                                                            setEditedVendor({ ...editedVendor, stellarSupplierName: e.target.value });
                                                            setSearchQuery(e.target.value);
                                                            if (e.target.value.length > 2) searchStellarSuppliers(e.target.value);
                                                        }}
                                                        placeholder="Search or enter name..."
                                                        className="pr-8"
                                                    />
                                                    <div className="absolute right-2 top-1/2 -translate-y-1/2 text-muted-foreground">
                                                        {isSearching ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Search className="w-3.5 h-3.5" />}
                                                    </div>
                                                </div>

                                                {showResults && searchResults.length > 0 && (
                                                    <div className="absolute z-50 w-full mt-1 bg-white border rounded shadow-lg max-h-[200px] overflow-auto">
                                                        {searchResults.map((s: any, i) => (
                                                            <div
                                                                key={i}
                                                                className="px-3 py-2 text-sm hover:bg-blue-50 cursor-pointer border-b last:border-0"
                                                                onClick={() => selectStellarSupplier(s)}
                                                            >
                                                                <p className="font-semibold text-xs">{s.name}</p>
                                                                <p className="text-[10px] text-muted-foreground font-mono">{s.id || s.uuid}</p>
                                                            </div>
                                                        ))}
                                                    </div>
                                                )}
                                            </div>
                                            <p className="text-[10px] text-muted-foreground italic leading-tight">
                                                Obtain these values from the Stellar API or Chain Flow Metrics configuration.
                                            </p>
                                        </>
                                    ) : (
                                        <>
                                            <div className="space-y-3">
                                                <div>
                                                    <Label className="text-[10px] text-muted-foreground uppercase tracking-tight">Status</Label>
                                                    <div className="flex items-center gap-2 mt-0.5">
                                                        {vendor.stellarSupplierId ? (
                                                            <>
                                                                <CheckCircle className="w-4 h-4 text-green-500" />
                                                                <span className="text-sm font-medium text-green-700">Configured</span>
                                                            </>
                                                        ) : (
                                                            <>
                                                                <AlertCircle className="w-4 h-4 text-amber-500" />
                                                                <span className="text-sm font-medium text-amber-600">Not Configured</span>
                                                            </>
                                                        )}
                                                    </div>
                                                </div>

                                                {vendor.stellarSupplierId && (
                                                    <>
                                                        <div>
                                                            <Label className="text-[10px] text-muted-foreground uppercase tracking-tight">System Name</Label>
                                                            <p className="text-sm font-medium">{vendor.stellarSupplierName || '—'}</p>
                                                        </div>
                                                        <div>
                                                            <Label className="text-[10px] text-muted-foreground uppercase tracking-tight">ID</Label>
                                                            <p className="text-[11px] font-mono bg-muted p-1.5 rounded border">{vendor.stellarSupplierId}</p>
                                                        </div>
                                                    </>
                                                )}
                                            </div>
                                        </>
                                    )}

                                    {suggestion && !vendor.stellarSupplierId && !isEditing && (
                                        <div className="bg-amber-50 border border-amber-200 p-3 rounded-lg space-y-2 mt-2">
                                            <div className="flex items-center gap-2">
                                                <AlertTriangle className="w-4 h-4 text-amber-600" />
                                                <span className="text-xs font-bold text-amber-900">SUGGESTED MAPPING</span>
                                            </div>
                                            <div className="text-[11px] text-amber-800 leading-tight">
                                                We found a matching Stellar Supplier ID used by other stores in your organization.
                                            </div>
                                            <Button
                                                variant="outline"
                                                size="sm"
                                                className="w-full text-xs h-7 border-amber-300 text-amber-900 bg-white hover:bg-amber-100"
                                                onClick={applySuggestion}
                                            >
                                                Use {suggestion.stellarSupplierName}
                                            </Button>
                                        </div>
                                    )}
                                </CardContent>
                            </Card>
                        </div>
                    </div>
                </TabsContent>
            </Tabs>
        </div>
    );
}
