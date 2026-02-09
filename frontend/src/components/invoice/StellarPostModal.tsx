import { useState, useEffect } from 'react';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter } from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { AlertCircle, CheckCircle, Loader2, ArrowRight, Search, Building2, AlertTriangle, ShieldCheck } from 'lucide-react';
import { useAuth } from '@/context/AuthContext';
import { PreflightResponse, VendorResolutionInfo, BulkPostResult, PreflightIssue } from '@/types/invoice';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Progress } from '@/components/ui/progress';
import { toast } from 'sonner';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Badge } from '@/components/ui/badge';
import { Card } from '@/components/ui/card';

const API_BASE = import.meta.env.VITE_API_BASE ||
    (import.meta.env.PROD ? 'https://invoice-backend-a1gb.onrender.com' : 'http://localhost:8000');

interface StellarPostModalProps {
    invoiceIds: string[];
    open: boolean;
    onClose: () => void;
    onSuccess: () => void;
}

type Step = 'loading' | 'resolution' | 'ready' | 'posting' | 'success';

interface VendorMapState {
    [vendorName: string]: {
        id: string;
        name: string;
    }
}

export function StellarPostModal({ invoiceIds, open, onClose, onSuccess }: StellarPostModalProps) {
    const { getToken } = useAuth();
    const [step, setStep] = useState<Step>('loading');
    const [preflight, setPreflight] = useState<PreflightResponse | null>(null);
    const [result, setResult] = useState<BulkPostResult | null>(null);
    const [mappedVendors, setMappedVendors] = useState<VendorMapState>({});

    // Resolution State
    const [searchQuery, setSearchQuery] = useState('');
    const [searchResults, setSearchResults] = useState<any[]>([]);
    const [isSearching, setIsSearching] = useState(false);
    const [currentVendorIndex, setCurrentVendorIndex] = useState(0);

    // Posting State
    const [isPosting, setIsPosting] = useState(false);

    useEffect(() => {
        if (open && invoiceIds.length > 0) {
            runPreflight();
        } else {
            // Reset state on close
            setStep('loading');
            setPreflight(null);
            setResult(null);
            setMappedVendors({});
            setCurrentVendorIndex(0);
        }
    }, [open, invoiceIds]);

    const runPreflight = async () => {
        setStep('loading');
        try {
            const token = await getToken();
            const res = await fetch(`${API_BASE}/api/invoices/preflight-post`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    ...(token ? { Authorization: `Bearer ${token}` } : {})
                },
                body: JSON.stringify(invoiceIds)
            });
            if (!res.ok) throw new Error("Preflight failed");
            const data: PreflightResponse = await res.json();
            setPreflight(data);

            if (data.blockingVendors.length > 0) {
                setStep('resolution');
            } else {
                setStep('ready');
            }
        } catch (e) {
            toast.error("Failed to run preflight check");
            onClose();
        }
    };

    const handleSearch = async (query: string) => {
        setSearchQuery(query);
        if (query.length < 2) return;

        setIsSearching(true);
        try {
            const token = await getToken();
            const res = await fetch(`${API_BASE}/api/stellar/proxy/suppliers?name=${encodeURIComponent(query)}`, {
                headers: { ...(token ? { Authorization: `Bearer ${token}` } : {}) }
            });
            if (res.ok) {
                const data = await res.json();
                const items = data.items || data || [];
                setSearchResults(Array.isArray(items) ? items : []);
            }
        } catch (e) {
            console.error(e);
        } finally {
            setIsSearching(false);
        }
    };

    const handleSaveMapping = async (stellarId: string, stellarName: string) => {
        if (!preflight) return;

        const currentVendor = preflight.blockingVendors[currentVendorIndex];

        try {
            // We need to find the vendor ID to update it. 
            // The preflight gives us the vendor NAME.
            // We can search for the vendor by name or assuming we can find it via the first invoice.
            // A better way is to update the VENDOR based on the *Preflight* which should ideally return vendor IDs.
            // But our preflight returns vendor_name. 
            // We'll update the Global Mapping first, OR update the vendor by name via a new specialized endpoint?
            // Actually, `VendorDetail` updates via ID. 
            // Let's use a specialized endpoint: `POST /api/vendors/map-by-name`

            // For now, let's assume we can map by name via a new helper or existing logic.
            // I'll assume we have a `POST /api/vendors/map-by-name` or we iterate invoices to find vendor ID.
            // Hack for v1: Use `ensure_vendor_mapping` logic but forced? 
            // No, we need to save the manual selection.

            // Let's try to fetch the vendor by name from the backend first? Too slow.
            // Let's assume we implement a quick mapping endpoint on the fly or improved Preflight response.
            // For this implementation, I will assume a new endpoint: `POST /api/vendors/link-stellar`

            const token = await getToken();

            // Find one invoice ID to get the vendor ID? Or just use name?
            // Let's use name-based mapping endpoint which we will simulate/create.
            const res = await fetch(`${API_BASE}/api/vendors/link-stellar-by-name`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    ...(token ? { Authorization: `Bearer ${token}` } : {})
                },
                body: JSON.stringify({
                    vendorName: currentVendor.vendorName,
                    stellarSupplierId: stellarId,
                    stellarSupplierName: stellarName
                })
            });

            if (!res.ok) throw new Error("Failed to map vendor");

            toast.success(`Mapped ${currentVendor.vendorName}`);

            // Move to next
            if (currentVendorIndex < preflight.blockingVendors.length - 1) {
                setCurrentVendorIndex(prev => prev + 1);
                setSearchQuery('');
                setSearchResults([]);
            } else {
                // Done mapping, re-run preflight
                runPreflight();
            }

        } catch (e) {
            toast.error("Failed to save mapping");
        }
    };

    const handleExecutePost = async () => {
        if (!preflight) return;
        setIsPosting(true);
        setStep('posting');

        try {
            const token = await getToken();
            // Use ready_ids. If user ignores errors, we proceed.
            // If they want to fix errors, they would have closed the modal.

            const idsToPost = preflight.readyIds;

            const res = await fetch(`${API_BASE}/api/invoices/bulk-post`, {
                method: 'PATCH',
                headers: {
                    'Content-Type': 'application/json',
                    ...(token ? { Authorization: `Bearer ${token}` } : {})
                },
                body: JSON.stringify(idsToPost)
            });

            if (!res.ok) throw new Error("Post failed");

            const resultData: BulkPostResult = await res.json();
            // The backend returns { status: "completed", results: ... } 
            // My type might need adjustment or backend response wrapper.
            // Let's assume backend returns { status, results: BulkPostResult }
            // Actually backend returns { status: "completed", results: {success: [], failed: [], skipped: []} }

            // Extract the inner results
            const finalResult = (resultData as any).results || resultData;
            setResult(finalResult);

            setStep('success');
            onSuccess();

        } catch (e) {
            toast.error("Critical failure during posting");
            setStep('ready'); // Go back to ready?
        } finally {
            setIsPosting(false);
        }
    };

    // --- Sub-components (Render Helpers) ---

    const renderLoading = () => (
        <div className="flex flex-col items-center justify-center py-12 space-y-4">
            <Loader2 className="w-12 h-12 text-primary animate-spin" />
            <p className="text-gray-500 font-medium">Validating invoices & supplier mappings...</p>
        </div>
    );

    const renderResolution = () => {
        if (!preflight || preflight.blockingVendors.length === 0) return null;
        const currentVendor = preflight.blockingVendors[currentVendorIndex];
        const progress = ((currentVendorIndex) / preflight.blockingVendors.length) * 100;

        return (
            <div className="space-y-6">
                <div className="space-y-2">
                    <div className="flex justify-between text-sm text-gray-500">
                        <span>Mapping Suppliers ({currentVendorIndex + 1}/{preflight.blockingVendors.length})</span>
                        <span>{Math.round(progress)}%</span>
                    </div>
                    <Progress value={progress} className="h-2" />
                </div>

                <div className="bg-amber-50 border border-amber-200 rounded-lg p-4 flex gap-3">
                    <AlertTriangle className="w-5 h-5 text-amber-600 flex-shrink-0" />
                    <div>
                        <h4 className="font-semibold text-amber-900">Supplier Not Recognized</h4>
                        <p className="text-sm text-amber-800 mt-1">
                            We cannot post invoices for <strong>{currentVendor.vendorName}</strong> because it is not linked to a Stellar Supplier.
                        </p>
                    </div>
                </div>

                <div className="space-y-4">
                    <div className="space-y-2">
                        <Label>Search Stellar for "{currentVendor.vendorName}"</Label>
                        <div className="relative">
                            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
                            <Input
                                value={searchQuery}
                                onChange={e => handleSearch(e.target.value)}
                                placeholder="Type supplier name..."
                                className="pl-9"
                                autoFocus
                            />
                            {isSearching && (
                                <Loader2 className="absolute right-3 top-1/2 -translate-y-1/2 w-4 h-4 animate-spin text-gray-400" />
                            )}
                        </div>
                    </div>

                    <ScrollArea className="h-[200px] border rounded-md">
                        <div className="p-2 space-y-1">
                            {searchResults.length === 0 ? (
                                <div className="p-4 text-center text-gray-500 text-sm">
                                    {searchQuery.length < 2 ? "Type to search..." : "No suppliers found."}
                                </div>
                            ) : (
                                searchResults.map((s: any) => (
                                    <button
                                        key={s.id || s.uuid}
                                        onClick={() => handleSaveMapping(s.id || s.uuid, s.name)}
                                        className="w-full text-left px-3 py-2 rounded-md hover:bg-gray-100 flex items-center justify-between group transition-colors"
                                    >
                                        <div>
                                            <p className="font-medium text-sm group-hover:text-primary">{s.name}</p>
                                            <p className="text-xs text-gray-400 font-mono">{s.id || s.uuid}</p>
                                        </div>
                                        <ArrowRight className="w-4 h-4 text-gray-300 group-hover:text-primary" />
                                    </button>
                                ))
                            )}
                        </div>
                    </ScrollArea>
                </div>
            </div>
        );
    };

    const renderReady = () => {
        if (!preflight) return null;
        const hasErrors = preflight.issues.some(i => i.issueType === 'blocking');
        const readyCount = preflight.readyIds.length;

        return (
            <div className="space-y-6">
                <div className="flex items-center gap-4 p-4 bg-green-50 border border-green-200 rounded-lg">
                    <div className="bg-green-100 p-2 rounded-full">
                        <ShieldCheck className="w-6 h-6 text-green-600" />
                    </div>
                    <div>
                        <h4 className="font-semibold text-green-900">Ready to Post</h4>
                        <p className="text-sm text-green-800">
                            {readyCount} invoice{readyCount !== 1 ? 's' : ''} validated and ready for Stellar.
                        </p>
                    </div>
                </div>

                {preflight.issues.length > 0 && (
                    <div className="space-y-3">
                        <h5 className="font-medium text-sm text-gray-700">Warnings & Errors</h5>
                        <ScrollArea className="h-[150px] border rounded-md p-2 bg-gray-50">
                            <div className="space-y-2">
                                {preflight.issues.map((issue, idx) => (
                                    <div key={idx} className="flex gap-2 text-sm p-2 bg-white rounded border border-gray-100">
                                        {issue.issueType === 'blocking' ?
                                            <AlertCircle className="w-4 h-4 text-red-500 shrink-0" /> :
                                            <AlertTriangle className="w-4 h-4 text-amber-500 shrink-0" />
                                        }
                                        <div>
                                            <span className="font-medium text-gray-900">Invoice {issue.invoiceId.substring(0, 8)}...: </span>
                                            <span className="text-gray-600">{issue.message}</span>
                                        </div>
                                    </div>
                                ))}
                            </div>
                        </ScrollArea>
                        {hasErrors && (
                            <p className="text-xs text-gray-500 italic">
                                * Invoices with blocking errors will be skipped.
                            </p>
                        )}
                    </div>
                )}
            </div>
        );
    };

    const renderPosting = () => (
        <div className="flex flex-col items-center justify-center py-12 space-y-6">
            <div className="relative">
                <div className="absolute inset-0 bg-primary/20 rounded-full animate-ping"></div>
                <div className="relative bg-primary text-white p-4 rounded-full">
                    <ArrowRight className="w-8 h-8" />
                </div>
            </div>
            <div className="text-center space-y-2">
                <h3 className="text-lg font-semibold">Posting to Stellar...</h3>
                <p className="text-gray-500">Sending invoices to the Point of Sale system.</p>
            </div>
            <Progress value={66} className="w-full max-w-xs animate-pulse" />
        </div>
    );

    const renderSuccess = () => {
        if (!result) return null;
        const successCount = (result.success || []).length;
        const failCount = (result.failed || []).length;

        return (
            <div className="space-y-6">
                <div className="text-center py-6">
                    <div className="mx-auto bg-green-100 p-4 rounded-full w-fit mb-4">
                        <CheckCircle className="w-10 h-10 text-green-600" />
                    </div>
                    <h3 className="text-2xl font-bold text-gray-900">Operation Complete</h3>
                    <p className="text-gray-500">
                        Successfully posted {successCount} invoice{successCount !== 1 ? 's' : ''}.
                    </p>
                </div>

                {failCount > 0 && (
                    <div className="border rounded-md p-4 bg-red-50 border-red-100">
                        <h4 className="font-semibold text-red-900 mb-2">{failCount} Failed</h4>
                        <ul className="text-sm space-y-1 text-red-800">
                            {result.failed.map((f: any, i: number) => (
                                <li key={i}>• {f.id.substring(0, 8)}: {f.reason}</li>
                            ))}
                        </ul>
                    </div>
                )}
            </div>
        );
    };

    // --- Main Render ---

    return (
        <Dialog open={open} onOpenChange={(v) => { if (!v && step !== 'posting') onClose(); }}>
            <DialogContent className="sm:max-w-[600px]">
                <DialogHeader>
                    <DialogTitle>Post to Stellar</DialogTitle>
                    <DialogDescription>
                        Sync your approved invoices to the Point of Sale system.
                    </DialogDescription>
                </DialogHeader>

                <div className="py-4">
                    {step === 'loading' && renderLoading()}
                    {step === 'resolution' && renderResolution()}
                    {step === 'ready' && renderReady()}
                    {step === 'posting' && renderPosting()}
                    {step === 'success' && renderSuccess()}
                </div>

                <DialogFooter>
                    {step === 'resolution' && (
                        <Button variant="ghost" onClick={onClose}>Cancel</Button>
                    )}

                    {step === 'ready' && (
                        <>
                            <Button variant="outline" onClick={onClose}>Cancel</Button>
                            <Button
                                onClick={handleExecutePost}
                                disabled={preflight?.readyIds.length === 0}
                                className="bg-indigo-600 hover:bg-indigo-700 text-white"
                            >
                                Post {preflight?.readyIds.length} Invoices
                            </Button>
                        </>
                    )}

                    {step === 'success' && (
                        <Button onClick={onClose}>Done</Button>
                    )}
                </DialogFooter>
            </DialogContent>
        </Dialog>
    );
}
