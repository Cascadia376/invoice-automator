
import { useState, useEffect } from "react";
import { useAuth } from "@/context/AuthContext";
import { Issue } from "@/types/invoice";
import {
    AlertCircle,
    CheckCircle2,
    Clock,
    Filter,
    Search,
    ArrowUpRight,
    MoreVertical,
    Mail,
    MessageSquare
} from "lucide-react";
import { formatCurrency } from "@/lib/utils";
import { format } from "date-fns";
import { useNavigate } from "react-router-dom";
import { toast } from "sonner";
import {
    Card,
    CardContent,
    CardHeader,
    CardTitle
} from "@/components/ui/card";
import {
    Table,
    TableBody,
    TableCell,
    TableHead,
    TableHeader,
    TableRow
} from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
    DropdownMenu,
    DropdownMenuContent,
    DropdownMenuItem,
    DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";

export default function IssueTracker() {
    const { getToken } = useAuth();
    const navigate = useNavigate();
    const [issues, setIssues] = useState<Issue[]>([]);
    const [loading, setLoading] = useState(true);
    const [searchTerm, setSearchTerm] = useState("");
    const [statusFilter, setStatusFilter] = useState("all");

    const fetchIssues = async () => {
        try {
            const token = await getToken();
            const API_BASE = import.meta.env.PROD ? 'https://invoice-backend-a1gb.onrender.com' : 'http://localhost:8000';
            const response = await fetch(`${API_BASE}/api/issues`, {
                headers: { ...(token ? { 'Authorization': `Bearer ${token}` } : {}) }
            });
            if (!response.ok) throw new Error("Failed to fetch issues");
            const data = await response.json();
            setIssues(data);
        } catch (error) {
            console.error(error);
            toast.error("Failed to load issues");
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchIssues();
    }, []);

    const filteredIssues = issues.filter(issue => {
        const matchesSearch =
            (issue.vendorName?.toLowerCase().includes(searchTerm.toLowerCase()) ||
                issue.invoiceNumber?.toLowerCase().includes(searchTerm.toLowerCase()) ||
                issue.description?.toLowerCase().includes(searchTerm.toLowerCase()));

        const matchesStatus = statusFilter === "all" || issue.status === statusFilter;

        return matchesSearch && matchesStatus;
    });

    const getStatusBadge = (status: string) => {
        switch (status) {
            case 'open': return <Badge variant="outline" className="bg-red-50 text-red-700 border-red-200">Open</Badge>;
            case 'reported': return <Badge variant="outline" className="bg-blue-50 text-blue-700 border-blue-200">Reported</Badge>;
            case 'resolved': return <Badge variant="outline" className="bg-green-50 text-green-700 border-green-200">Resolved</Badge>;
            case 'closed': return <Badge variant="outline" className="bg-gray-50 text-gray-700 border-gray-200">Closed</Badge>;
            default: return <Badge variant="outline">{status}</Badge>;
        }
    };

    const getTypeBadge = (type: string) => {
        const label = type.replace('_', ' ').replace(/\b\w/g, l => l.toUpperCase());
        return <span className="text-xs font-medium text-gray-600 px-2 py-0.5 bg-gray-100 rounded-full">{label}</span>;
    };

    return (
        <div className="space-y-6">
            <div className="flex justify-between items-center">
                <div>
                    <h1 className="text-3xl font-black tracking-tight text-gray-900">Issue Tracker</h1>
                    <p className="text-gray-500 mt-1">Track and resolve discrepancies with invoice shipments and pricing.</p>
                </div>
                <div className="flex gap-2">
                    <Button variant="outline" onClick={fetchIssues} size="sm" className="gap-2">
                        <Clock className="h-4 w-4" />
                        Refresh
                    </Button>
                </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <Card className="bg-white border-red-100 border-2">
                    <CardHeader className="pb-2">
                        <CardTitle className="text-sm font-medium text-gray-500">Open Issues</CardTitle>
                    </CardHeader>
                    <CardContent>
                        <div className="flex items-center justify-between">
                            <div className="text-2xl font-bold text-red-600">{issues.filter(i => i.status === 'open').length}</div>
                            <AlertCircle className="h-8 w-8 text-red-100" />
                        </div>
                    </CardContent>
                </Card>
                <Card className="bg-white border-blue-100 border-2">
                    <CardHeader className="pb-2">
                        <CardTitle className="text-sm font-medium text-gray-500">Reported (Pending)</CardTitle>
                    </CardHeader>
                    <CardContent>
                        <div className="flex items-center justify-between">
                            <div className="text-2xl font-bold text-blue-600">{issues.filter(i => i.status === 'reported').length}</div>
                            <Clock className="h-8 w-8 text-blue-100" />
                        </div>
                    </CardContent>
                </Card>
                <Card className="bg-white border-green-100 border-2">
                    <CardHeader className="pb-2">
                        <CardTitle className="text-sm font-medium text-gray-500">Resolved Today</CardTitle>
                    </CardHeader>
                    <CardContent>
                        <div className="flex items-center justify-between">
                            <div className="text-2xl font-bold text-green-600">{issues.filter(i => i.status === 'resolved').length}</div>
                            <CheckCircle2 className="h-8 w-8 text-green-100" />
                        </div>
                    </CardContent>
                </Card>
            </div>

            <Card className="bg-white border-none shadow-sm">
                <CardHeader className="border-b bg-gray-50/50">
                    <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
                        <div className="relative flex-1 max-w-sm">
                            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400" />
                            <Input
                                placeholder="Search vendor, invoice, or issue..."
                                className="pl-9"
                                value={searchTerm}
                                onChange={(e) => setSearchTerm(e.target.value)}
                            />
                        </div>
                        <div className="flex items-center gap-2">
                            <Filter className="h-4 w-4 text-gray-400" />
                            <div className="flex gap-1 p-1 bg-gray-100 rounded-md">
                                {['all', 'open', 'reported', 'resolved'].map((s) => (
                                    <button
                                        key={s}
                                        onClick={() => setStatusFilter(s)}
                                        className={`px-3 py-1 text-xs font-medium rounded transition-all ${statusFilter === s ? 'bg-white shadow-sm text-gray-900' : 'text-gray-500 hover:text-gray-700'
                                            }`}
                                    >
                                        {s.charAt(0).toUpperCase() + s.slice(1)}
                                    </button>
                                ))}
                            </div>
                        </div>
                    </div>
                </CardHeader>
                <CardContent className="p-0">
                    <Table>
                        <TableHeader className="bg-gray-50/50">
                            <TableRow>
                                <TableHead>Vendor & Invoice</TableHead>
                                <TableHead>Type</TableHead>
                                <TableHead>Description</TableHead>
                                <TableHead>Status</TableHead>
                                <TableHead>Created</TableHead>
                                <TableHead className="text-right">Action</TableHead>
                            </TableRow>
                        </TableHeader>
                        <TableBody>
                            {loading ? (
                                <TableRow>
                                    <TableCell colSpan={6} className="text-center py-8 text-gray-500">Loading issues...</TableCell>
                                </TableRow>
                            ) : filteredIssues.length === 0 ? (
                                <TableRow>
                                    <TableCell colSpan={6} className="text-center py-16 text-gray-500">
                                        <div className="flex flex-col items-center gap-2">
                                            <AlertCircle className="h-10 w-10 text-gray-200" />
                                            <p className="font-medium">No issues found</p>
                                            <p className="text-sm">Discrepancies reported on invoices will appear here.</p>
                                        </div>
                                    </TableCell>
                                </TableRow>
                            ) : (
                                filteredIssues.map((issue) => (
                                    <TableRow key={issue.id} className="hover:bg-gray-50/50 transition-colors cursor-pointer" onClick={() => navigate(`/invoices/${issue.invoiceId}`)}>
                                        <TableCell className="py-4">
                                            <div className="flex flex-col">
                                                <span className="font-bold text-gray-900">{issue.vendorName}</span>
                                                <span className="text-xs text-gray-500 font-mono">#{issue.invoiceNumber}</span>
                                            </div>
                                        </TableCell>
                                        <TableCell>{getTypeBadge(issue.type)}</TableCell>
                                        <TableCell className="max-w-xs truncate text-sm text-gray-600">
                                            {issue.description || <span className="text-gray-300 italic">No description</span>}
                                        </TableCell>
                                        <TableCell>{getStatusBadge(issue.status)}</TableCell>
                                        <TableCell className="text-xs text-gray-500">
                                            {format(new Date(issue.createdAt), 'MMM d, yyyy')}
                                        </TableCell>
                                        <TableCell className="text-right" onClick={(e) => e.stopPropagation()}>
                                            <div className="flex justify-end gap-1">
                                                <Button variant="ghost" size="icon" className="h-8 w-8 text-blue-600 hover:text-blue-700 hover:bg-blue-50" title="Inform Vendor">
                                                    <Mail className="h-4 w-4" />
                                                </Button>
                                                <DropdownMenu>
                                                    <DropdownMenuTrigger asChild>
                                                        <Button variant="ghost" size="icon" className="h-8 w-8">
                                                            <MoreVertical className="h-4 w-4" />
                                                        </Button>
                                                    </DropdownMenuTrigger>
                                                    <DropdownMenuContent align="end">
                                                        <DropdownMenuItem onClick={() => navigate(`/invoices/${issue.invoiceId}`)}>
                                                            View Invoice
                                                        </DropdownMenuItem>
                                                        <DropdownMenuItem>
                                                            Add Communication Note
                                                        </DropdownMenuItem>
                                                        <DropdownMenuItem className="text-green-600 font-medium">
                                                            Mark as Resolved
                                                        </DropdownMenuItem>
                                                    </DropdownMenuContent>
                                                </DropdownMenu>
                                            </div>
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
