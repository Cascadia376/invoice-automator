import { useState, useEffect } from "react";
import { useInvoice } from "@/context/InvoiceContext";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useSearchParams } from "react-router-dom";
import {
    Table,
    TableBody,
    TableCell,
    TableHead,
    TableHeader,
    TableRow,
} from "@/components/ui/table";
import {
    Dialog,
    DialogContent,
    DialogDescription,
    DialogFooter,
    DialogHeader,
    DialogTitle,
    DialogTrigger,
} from "@/components/ui/dialog";
import { Plus, Pencil, Trash2, Loader2, Gem, Wallet } from "lucide-react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import * as z from "zod";
import { GLCategory } from "@/types/invoice";
import { useAuth } from "@clerk/clerk-react";

const categorySchema = z.object({
    code: z.string().min(1, "Code is required"),
    name: z.string().min(1, "Name is required"),
});

type CategoryFormData = z.infer<typeof categorySchema>;

export default function Settings() {
    const { glCategories, createGLCategory, updateGLCategory, deleteGLCategory } = useInvoice();
    const [isDialogOpen, setIsDialogOpen] = useState(false);
    const [editingCategory, setEditingCategory] = useState<GLCategory | null>(null);
    const [isLoading, setIsLoading] = useState(false);

    const {
        register,
        handleSubmit,
        reset,
        setValue,
        formState: { errors },
    } = useForm<CategoryFormData>({
        resolver: zodResolver(categorySchema),
    });

    const onSubmit = async (data: CategoryFormData) => {
        setIsLoading(true);
        try {
            const full_name = `${data.code} - ${data.name}`;
            if (editingCategory) {
                await updateGLCategory(editingCategory.id, {
                    code: data.code,
                    name: data.name,
                    fullName: full_name
                });
            } else {
                await createGLCategory({
                    code: data.code,
                    name: data.name,
                    fullName: full_name
                });
            }
            setIsDialogOpen(false);
            reset();
            setEditingCategory(null);
        } catch (error) {
            console.error(error);
        } finally {
            setIsLoading(false);
        }
    };

    const handleEdit = (category: GLCategory) => {
        setEditingCategory(category);
        setValue("code", category.code);
        setValue("name", category.name);
        setIsDialogOpen(true);
    };

    const handleDelete = async (id: string) => {
        if (confirm("Are you sure you want to delete this category?")) {
            await deleteGLCategory(id);
        }
    };

    const openAddDialog = () => {
        setEditingCategory(null);
        reset({ code: "", name: "" });
        setIsDialogOpen(true);
    };

    const [qboStatus, setQboStatus] = useState<{ connected: boolean; realm_id?: string; updated_at?: string } | null>(null);

    useEffect(() => {
        checkQboStatus();
    }, []);

    const checkQboStatus = async () => {
        try {
            const response = await fetch(`${import.meta.env.PROD ? 'https://invoice-processor-backend.onrender.com' : 'http://localhost:8000'}/api/auth/qbo/status`);
            const data = await response.json();
            setQboStatus(data);
        } catch (error) {
            console.error("Failed to check QBO status:", error);
        }
    };

    const handleConnectQbo = async () => {
        try {
            const response = await fetch(`${import.meta.env.PROD ? 'https://invoice-processor-backend.onrender.com' : 'http://localhost:8000'}/api/auth/qbo/connect`);
            const data = await response.json();
            if (data.auth_url) {
                window.location.href = data.auth_url;
            }
        } catch (error) {
            console.error("Failed to get QBO auth URL:", error);
        }
    };

    const handleDisconnectQbo = async () => {
        if (!confirm("Are you sure you want to disconnect from QuickBooks?")) return;

        try {
            await fetch(`${import.meta.env.PROD ? 'https://invoice-processor-backend.onrender.com' : 'http://localhost:8000'}/api/auth/qbo/disconnect`, {
                method: "POST"
            });
            checkQboStatus();
        } catch (error) {
            console.error("Failed to disconnect QBO:", error);
        }
    };

    const [csvColumns, setCsvColumns] = useState<string[]>([
        "Invoice Number", "Date", "Vendor", "SKU", "Description",
        "Units/Case", "Cases", "Quantity", "Unit Cost", "Total", "Category/GL Code"
    ]);

    const availableColumns = [
        "Invoice Number", "Date", "Vendor", "SKU", "Description",
        "Units/Case", "Cases", "Quantity", "Unit Cost", "Total", "Category/GL Code"
    ];

    useEffect(() => {
        const savedColumns = localStorage.getItem("csv_export_columns");
        if (savedColumns) {
            setCsvColumns(JSON.parse(savedColumns));
        }
    }, []);

    const toggleColumn = (column: string) => {
        const newColumns = csvColumns.includes(column)
            ? csvColumns.filter(c => c !== column)
            : [...csvColumns, column];

        setCsvColumns(newColumns);
        localStorage.setItem("csv_export_columns", JSON.stringify(newColumns));
    };

    const { getToken } = useAuth();
    const [searchParams] = useSearchParams();

    useEffect(() => {
        if (searchParams.get("success")) {
            alert("Subscription successful! You are now on the Pro plan.");
        }
        if (searchParams.get("canceled")) {
            alert("Subscription cancelled.");
        }
    }, [searchParams]);

    const handleUpgrade = async () => {
        try {
            const token = await getToken();
            const response = await fetch(`${import.meta.env.PROD ? 'https://invoice-processor-backend.onrender.com' : 'http://localhost:8000'}/api/billing/create-checkout-session`, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    "Authorization": `Bearer ${token}`
                },
                body: JSON.stringify({
                    price_id: "price_1234567890" // Replace with actual Stripe Price ID
                })
            });

            if (!response.ok) throw new Error("Failed to create checkout session");

            const data = await response.json();
            if (data.url) {
                window.location.href = data.url;
            }
        } catch (error) {
            console.error("Upgrade failed:", error);
            alert("Failed to start upgrade process. Please try again.");
        }
    };

    return (
        <div className="space-y-8">
            <div>
                <h3 className="text-lg font-medium">Settings</h3>
                <p className="text-sm text-muted-foreground">
                    Manage your account settings and preferences.
                </p>
            </div>

            {/* Subscription Settings */}
            <div className="space-y-4">
                <div>
                    <h4 className="text-base font-medium">Subscription</h4>
                    <p className="text-sm text-muted-foreground">
                        Manage your billing and subscription plan.
                    </p>
                </div>
                <div className="border rounded-md p-4 bg-white">
                    <div className="flex items-center justify-between">
                        <div className="flex items-center gap-3">
                            <div className="h-10 w-10 rounded-full bg-purple-100 flex items-center justify-center">
                                <Gem className="h-5 w-5 text-purple-600" />
                            </div>
                            <div>
                                <h5 className="font-medium text-sm">Pro Plan</h5>
                                <p className="text-xs text-muted-foreground">
                                    Unlock unlimited invoices and advanced features.
                                </p>
                            </div>
                        </div>
                        <Button onClick={handleUpgrade} className="bg-gradient-to-r from-purple-600 to-indigo-600 text-white hover:from-purple-700 hover:to-indigo-700">
                            Upgrade to Pro
                        </Button>
                    </div>
                </div>
            </div>

            {/* QuickBooks Integration */}
            <div className="space-y-4">
                <div>
                    <h4 className="text-base font-medium">QuickBooks Online</h4>
                    <p className="text-sm text-muted-foreground">
                        Connect your QuickBooks Online account to export invoices as bills.
                    </p>
                </div>
                <div className="border rounded-md p-4 bg-white">
                    <div className="flex items-center justify-between">
                        <div className="flex items-center gap-3">
                            <div className={`h-10 w-10 rounded-full flex items-center justify-center ${qboStatus?.connected ? 'bg-green-100' : 'bg-gray-100'}`}>
                                <Wallet className="h-5 w-5 text-gray-600" />
                            </div>
                            <div>
                                <h5 className="font-medium text-sm">QuickBooks Connection</h5>
                                <p className="text-xs text-muted-foreground">
                                    {qboStatus?.connected
                                        ? `Connected to Company ID: ${qboStatus.realm_id}`
                                        : "Not connected"}
                                </p>
                            </div>
                        </div>
                        {qboStatus?.connected ? (
                            <Button variant="outline" onClick={handleDisconnectQbo} className="text-destructive hover:text-destructive">
                                Disconnect
                            </Button>
                        ) : (
                            <Button onClick={handleConnectQbo} className="bg-[#2CA01C] hover:bg-[#238216] text-white">
                                Connect to QuickBooks
                            </Button>
                        )}
                    </div>
                </div>
            </div>

            {/* CSV Export Settings */}
            <div className="space-y-4">
                <div>
                    <h4 className="text-base font-medium">CSV Export</h4>
                    <p className="text-sm text-muted-foreground">
                        Customize the columns included in your CSV exports. You can rename headers to match your accounting software.
                    </p>
                </div>
                <div className="border rounded-md bg-white">
                    <Table>
                        <TableHeader>
                            <TableRow>
                                <TableHead className="w-[50px]"></TableHead>
                                <TableHead>Field Name</TableHead>
                                <TableHead>Export Header</TableHead>
                            </TableRow>
                        </TableHeader>
                        <TableBody>
                            {availableColumns.map((col) => {
                                const isEnabled = csvColumns.includes(col);
                                const currentConfig = localStorage.getItem("csv_export_config");
                                const configMap = currentConfig ? JSON.parse(currentConfig) : {};
                                const customHeader = configMap[col] || col;

                                return (
                                    <TableRow key={col}>
                                        <TableCell>
                                            <input
                                                type="checkbox"
                                                checked={isEnabled}
                                                onChange={() => toggleColumn(col)}
                                                className="h-4 w-4 rounded border-gray-300 text-primary focus:ring-primary"
                                            />
                                        </TableCell>
                                        <TableCell className="font-medium text-sm text-muted-foreground">
                                            {col}
                                        </TableCell>
                                        <TableCell>
                                            <Input
                                                disabled={!isEnabled}
                                                value={customHeader}
                                                onChange={(e) => {
                                                    const newConfig = { ...configMap, [col]: e.target.value };
                                                    localStorage.setItem("csv_export_config", JSON.stringify(newConfig));
                                                    // Force re-render (hacky but simple)
                                                    setCsvColumns([...csvColumns]);
                                                }}
                                                className="h-8 max-w-[250px]"
                                            />
                                        </TableCell>
                                    </TableRow>
                                );
                            })}
                        </TableBody>
                    </Table>
                </div>
            </div>

            <div className="space-y-4">
                <div className="flex items-center justify-between">
                    <div>
                        <h4 className="text-base font-medium">GL Categories</h4>
                        <p className="text-sm text-muted-foreground">
                            Manage General Ledger categories for invoice line items.
                        </p>
                    </div>
                    <Dialog open={isDialogOpen} onOpenChange={setIsDialogOpen}>
                        <DialogTrigger asChild>
                            <Button onClick={openAddDialog}>
                                <Plus className="h-4 w-4 mr-2" />
                                Add Category
                            </Button>
                        </DialogTrigger>
                        <DialogContent>
                            <DialogHeader>
                                <DialogTitle>{editingCategory ? "Edit Category" : "Add Category"}</DialogTitle>
                                <DialogDescription>
                                    {editingCategory ? "Update the GL category details." : "Create a new GL category for classification."}
                                </DialogDescription>
                            </DialogHeader>
                            <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
                                <div className="space-y-2">
                                    <Label htmlFor="code">GL Code</Label>
                                    <Input id="code" placeholder="e.g. 6010" {...register("code")} />
                                    {errors.code && <p className="text-sm text-destructive">{errors.code.message}</p>}
                                </div>
                                <div className="space-y-2">
                                    <Label htmlFor="name">Category Name</Label>
                                    <Input id="name" placeholder="e.g. Marketing & Advertising" {...register("name")} />
                                    {errors.name && <p className="text-sm text-destructive">{errors.name.message}</p>}
                                </div>
                                <DialogFooter>
                                    <Button type="button" variant="outline" onClick={() => setIsDialogOpen(false)}>
                                        Cancel
                                    </Button>
                                    <Button type="submit" disabled={isLoading}>
                                        {isLoading && <Loader2 className="h-4 w-4 mr-2 animate-spin" />}
                                        {editingCategory ? "Save Changes" : "Create Category"}
                                    </Button>
                                </DialogFooter>
                            </form>
                        </DialogContent>
                    </Dialog>
                </div>

                <div className="border rounded-md">
                    <Table>
                        <TableHeader>
                            <TableRow>
                                <TableHead>Code</TableHead>
                                <TableHead>Name</TableHead>
                                <TableHead>Full Name</TableHead>
                                <TableHead className="w-[100px] text-right">Actions</TableHead>
                            </TableRow>
                        </TableHeader>
                        <TableBody>
                            {glCategories.length === 0 ? (
                                <TableRow>
                                    <TableCell colSpan={4} className="text-center py-8 text-muted-foreground">
                                        No categories found. Add one to get started.
                                    </TableCell>
                                </TableRow>
                            ) : (
                                glCategories.map((category) => (
                                    <TableRow key={category.id}>
                                        <TableCell className="font-medium">{category.code}</TableCell>
                                        <TableCell>{category.name}</TableCell>
                                        <TableCell className="text-muted-foreground">{category.fullName}</TableCell>
                                        <TableCell className="text-right">
                                            <div className="flex justify-end gap-2">
                                                <Button
                                                    variant="ghost"
                                                    size="icon"
                                                    className="h-8 w-8"
                                                    onClick={() => handleEdit(category)}
                                                >
                                                    <Pencil className="h-4 w-4" />
                                                </Button>
                                                <Button
                                                    variant="ghost"
                                                    size="icon"
                                                    className="h-8 w-8 text-destructive hover:text-destructive"
                                                    onClick={() => handleDelete(category.id)}
                                                >
                                                    <Trash2 className="h-4 w-4" />
                                                </Button>
                                            </div>
                                        </TableCell>
                                    </TableRow>
                                ))
                            )}
                        </TableBody>
                    </Table>
                </div>
            </div>
        </div>
    );
}
