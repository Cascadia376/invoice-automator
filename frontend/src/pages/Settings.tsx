import { useState, useEffect } from "react";
import { useInvoice } from "@/context/InvoiceContext";
import { useAuth } from "@/context/AuthContext";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
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
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from "@/components/ui/select";
import { Plus, Pencil, Trash2, Loader2, Shield } from "lucide-react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import * as z from "zod";
import { GLCategory } from "@/types/invoice";

const categorySchema = z.object({
    code: z.string().min(1, "Code is required"),
    name: z.string().min(1, "Name is required"),
});

type CategoryFormData = z.infer<typeof categorySchema>;

interface UserRole {
    user_id: string;
    roles: string[];
}

export default function Settings() {
    const { glCategories, createGLCategory, updateGLCategory, deleteGLCategory } = useInvoice();
    const { isAdmin, getToken } = useAuth();

    // GL Category State
    const [isDialogOpen, setIsDialogOpen] = useState(false);
    const [editingCategory, setEditingCategory] = useState<GLCategory | null>(null);
    const [isLoading, setIsLoading] = useState(false);

    // User Management State
    const [users, setUsers] = useState<UserRole[]>([]);
    const [loadingUsers, setLoadingUsers] = useState(false);

    const {
        register,
        handleSubmit,
        reset,
        setValue,
        formState: { errors },
    } = useForm<CategoryFormData>({
        resolver: zodResolver(categorySchema),
    });

    // Fetch Users (Admin Only)
    useEffect(() => {
        if (isAdmin) {
            fetchUsers();
        }
    }, [isAdmin]);

    const fetchUsers = async () => {
        setLoadingUsers(true);
        try {
            const token = await getToken();
            const res = await fetch(`${import.meta.env.VITE_API_URL || 'https://invoice-backend-a1gb.onrender.com'}/api/admin/users`, {
                headers: { Authorization: `Bearer ${token}` }
            });
            if (res.ok) {
                const data = await res.json();
                setUsers(data);
            }
        } catch (e) {
            console.error("Failed to fetch users", e);
        } finally {
            setLoadingUsers(false);
        }
    };

    const handleRoleUpdate = async (userId: string, newRole: string) => {
        try {
            const token = await getToken();
            const res = await fetch(`${import.meta.env.VITE_API_URL || 'https://invoice-backend-a1gb.onrender.com'}/api/admin/users/${userId}/roles`, {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json',
                    Authorization: `Bearer ${token}`
                },
                body: JSON.stringify({ roles: [newRole] }) // Single role enforcement for now
            });

            if (res.ok) {
                await fetchUsers();
            }
        } catch (e) {
            console.error("Failed to update role", e);
        }
    };

    // GL Functions
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

    // CSV State
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

    return (
        <div className="space-y-8">
            <div>
                <h3 className="text-lg font-medium">Settings</h3>
                <p className="text-sm text-muted-foreground">
                    Manage your account settings and preferences.
                </p>
            </div>

            <Tabs defaultValue="general" className="w-full">
                <TabsList>
                    <TabsTrigger value="general">General</TabsTrigger>
                    {isAdmin && <TabsTrigger value="team">Team & Roles</TabsTrigger>}
                </TabsList>

                <TabsContent value="general" className="space-y-8 mt-4">
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
                </TabsContent>

                {isAdmin && (
                    <TabsContent value="team" className="space-y-4 mt-4">
                        <div>
                            <h4 className="text-base font-medium">Team Management</h4>
                            <p className="text-sm text-muted-foreground">
                                Manage user roles and permissions.
                            </p>
                        </div>

                        <div className="border rounded-md">
                            <Table>
                                <TableHeader>
                                    <TableRow>
                                        <TableHead>User ID</TableHead>
                                        <TableHead>Role</TableHead>
                                        <TableHead className="w-[200px]">Actions</TableHead>
                                    </TableRow>
                                </TableHeader>
                                <TableBody>
                                    {loadingUsers ? (
                                        <TableRow>
                                            <TableCell colSpan={3} className="text-center py-8">
                                                <Loader2 className="h-6 w-6 animate-spin mx-auto text-muted-foreground" />
                                            </TableCell>
                                        </TableRow>
                                    ) : users.length === 0 ? (
                                        <TableRow>
                                            <TableCell colSpan={3} className="text-center py-8 text-muted-foreground">
                                                No users found.
                                            </TableCell>
                                        </TableRow>
                                    ) : (
                                        users.map((u) => (
                                            <TableRow key={u.user_id}>
                                                <TableCell className="font-medium">
                                                    <div className="flex items-center gap-2">
                                                        <Shield className="h-4 w-4 text-muted-foreground" />
                                                        {u.user_id}
                                                    </div>
                                                </TableCell>
                                                <TableCell>
                                                    <div className="flex gap-1 flex-wrap">
                                                        {u.roles.map(r => (
                                                            <span key={r} className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-blue-100 text-blue-800">
                                                                {r}
                                                            </span>
                                                        ))}
                                                    </div>
                                                </TableCell>
                                                <TableCell>
                                                    <Select
                                                        defaultValue={u.roles[0] || 'staff'}
                                                        onValueChange={(val) => handleRoleUpdate(u.user_id, val)}
                                                    >
                                                        <SelectTrigger className="w-[140px]">
                                                            <SelectValue placeholder="Select role" />
                                                        </SelectTrigger>
                                                        <SelectContent>
                                                            <SelectItem value="admin">Admin</SelectItem>
                                                            <SelectItem value="manager">Manager</SelectItem>
                                                            <SelectItem value="staff">Staff</SelectItem>
                                                        </SelectContent>
                                                    </Select>
                                                </TableCell>
                                            </TableRow>
                                        ))
                                    )}
                                </TableBody>
                            </Table>
                        </div>
                    </TabsContent>
                )}
            </Tabs>
        </div>
    );
}
