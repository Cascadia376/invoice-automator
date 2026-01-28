import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
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
import { Plus, Pencil, Trash2, Loader2, Shield, Activity } from "lucide-react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import * as z from "zod";
import { GLCategory } from "@/types/invoice";

const categorySchema = z.object({
    code: z.string().min(1, "Code is required"),
    name: z.string().min(1, "Name is required"),
});

type CategoryFormData = z.infer<typeof categorySchema>;

const userSchema = z.object({
    email: z.string().email("Invalid email address"),
    role: z.enum(["admin", "manager", "staff"]),
    target_org_ids: z.array(z.string()).optional(),
});

const editUserSchema = z.object({
    email: z.string().email("Invalid email address"),
    first_name: z.string().optional(),
    last_name: z.string().optional(),
    role: z.enum(["admin", "manager", "staff"]),
    target_org_ids: z.array(z.string()).optional(),
});

type UserFormData = z.infer<typeof userSchema>;
type EditUserFormData = z.infer<typeof editUserSchema>;

interface StoreRef {
    id: string;
    name: string;
}

interface User {
    id: string;
    email: string;
    first_name?: string;
    last_name?: string;
    roles: string[];
    stores: StoreRef[];
    created_at?: string;
}

interface Organization {
    id: string;
    name: string;
}

export default function Settings() {
    const { glCategories, createGLCategory, updateGLCategory, deleteGLCategory } = useInvoice();
    const { isAdmin, getToken } = useAuth();
    const navigate = useNavigate();

    // GL Category State
    const [isDialogOpen, setIsDialogOpen] = useState(false);
    const [editingCategory, setEditingCategory] = useState<GLCategory | null>(null);
    const [isLoading, setIsLoading] = useState(false);

    // User Management State
    const [users, setUsers] = useState<User[]>([]);
    const [loadingUsers, setLoadingUsers] = useState(false);
    const [testResult, setTestResult] = useState<any>(null);

    const testAdminConnection = async () => {
        try {
            const token = await getToken();
            const res = await fetch(`${import.meta.env.VITE_API_URL || 'https://invoice-backend-a1gb.onrender.com'}/api/admin/connection-status`, {
                headers: { Authorization: `Bearer ${token}` }
            });
            const data = await res.json();
            setTestResult(data);
        } catch (e: any) {
            setTestResult({ error: e.toString() });
        }
    };
    const [isUserDialogOpen, setIsUserDialogOpen] = useState(false);
    const [isEditUserOpen, setIsEditUserOpen] = useState(false);
    const [editingUser, setEditingUser] = useState<User | null>(null);
    const [availableOrgs, setAvailableOrgs] = useState<Organization[]>([]);

    const {
        register,
        handleSubmit,
        reset,
        setValue,
        formState: { errors },
    } = useForm<CategoryFormData>({
        resolver: zodResolver(categorySchema),
    });

    const {
        register: registerUser,
        handleSubmit: handleSubmitUser,
        reset: resetUser,
        setValue: setValueUser,
        formState: { errors: userErrors },
        watch: watchUser
    } = useForm<UserFormData>({
        resolver: zodResolver(userSchema),
        defaultValues: { role: "staff" }
    });

    const {
        register: registerEditUser,
        handleSubmit: handleSubmitEditUser,
        reset: resetEditUser,
        setValue: setValueEditUser,
        formState: { errors: editUserErrors },
    } = useForm<EditUserFormData>({
        resolver: zodResolver(editUserSchema),
    });

    // Fetch Users & Orgs (Admin Only)
    useEffect(() => {
        if (isAdmin) {
            fetchUsers();
            fetchOrgs();
        }
    }, [isAdmin]);

    const fetchOrgs = async () => {
        try {
            const token = await getToken();
            const res = await fetch(`${import.meta.env.VITE_API_URL || 'https://invoice-backend-a1gb.onrender.com'}/api/admin/organizations`, {
                headers: { Authorization: `Bearer ${token}` }
            });
            if (res.ok) {
                const data = await res.json();
                setAvailableOrgs(data);
            }
        } catch (e) {
            console.error("Failed to fetch organizations", e);
        }
    };

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
            alert("Failed to load users. Check console for details.");
        } finally {
            setLoadingUsers(false);
        }
    };

    const handleUpdateUser = async (data: EditUserFormData) => {
        if (!editingUser) return;
        setLoadingUsers(true);
        try {
            const token = await getToken();
            const res = await fetch(`${import.meta.env.VITE_API_URL || 'https://invoice-backend-a1gb.onrender.com'}/api/admin/users/${editingUser.id}`, {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json',
                    Authorization: `Bearer ${token}`
                },
                body: JSON.stringify(data)
            });

            if (res.ok) {
                await fetchUsers();
                setIsEditUserOpen(false);
                setEditingUser(null);
            } else {
                const err = await res.json();
                alert(`Failed to update user: ${err.detail || 'Unknown error'}`);
            }
        } catch (e) {
            console.error("Error updating user", e);
            alert("Error updating user");
        } finally {
            setLoadingUsers(false);
        }
    };

    const handleDeleteUser = async (userId: string) => {
        if (!confirm("Are you sure you want to delete this user? This cannot be undone.")) return;

        try {
            const token = await getToken();
            const res = await fetch(`${import.meta.env.VITE_API_URL || 'https://invoice-backend-a1gb.onrender.com'}/api/admin/users/${userId}`, {
                method: 'DELETE',
                headers: { Authorization: `Bearer ${token}` }
            });

            if (res.ok) {
                await fetchUsers();
            } else {
                alert("Failed to delete user");
            }
        } catch (e) {
            console.error("Error deleting user", e);
        }
    };

    const openEditUser = (user: User) => {
        setEditingUser(user);
        resetEditUser({
            email: user.email,
            first_name: user.first_name || "",
            last_name: user.last_name || "",
            role: (user.roles[0] as "admin" | "manager" | "staff") || "staff",
            target_org_ids: user.stores.map(s => s.id)
        });
        setIsEditUserOpen(true);
    };

    const handleAddUser = async (data: UserFormData) => {
        setLoadingUsers(true);
        try {
            const token = await getToken();
            const res = await fetch(`${import.meta.env.VITE_API_URL || 'https://invoice-backend-a1gb.onrender.com'}/api/admin/users`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    Authorization: `Bearer ${token}`
                },
                body: JSON.stringify(data)
            });

            if (res.ok) {
                await fetchUsers();
                setIsUserDialogOpen(false);
                resetUser();
            } else {
                const err = await res.json();
                console.error("Failed to invite user", err);
                alert(`Failed to invite user: ${err.detail || 'Unknown error'}`);
            }
        } catch (e) {
            console.error("Error inviting user", e);
            alert("Error inviting user");
        } finally {
            setLoadingUsers(false);
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
                            <div className="flex gap-2">
                                <Button variant="secondary" onClick={() => navigate('/smoke-test')}>
                                    <Activity className="h-4 w-4 mr-2" />
                                    Run Smoke Test
                                </Button>
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
                        <div className="flex justify-between items-center bg-muted/50 p-4 rounded-lg border">
                            <div>
                                <h3 className="font-semibold">Troubleshoot Connection</h3>
                                <p className="text-xs text-muted-foreground">If users are not loading, check the backend status.</p>
                            </div>
                            <Button variant="outline" size="sm" onClick={testAdminConnection}>
                                Test Admin Connection
                            </Button>
                        </div>
                        {testResult && (
                            <div className="bg-slate-950 text-slate-50 p-4 rounded-md font-mono text-xs overflow-auto max-h-40">
                                <pre>{JSON.stringify(testResult, null, 2)}</pre>
                            </div>
                        )}

                        <div className="flex justify-between items-center">
                            <div>
                                <h4 className="text-base font-medium">Team Management</h4>
                                <p className="text-sm text-muted-foreground">
                                    Manage user roles and permissions.
                                </p>
                            </div>
                            <div className="flex gap-2">
                                <Dialog open={isUserDialogOpen} onOpenChange={setIsUserDialogOpen}>
                                    <DialogTrigger asChild>
                                        <Button onClick={() => { resetUser(); setIsUserDialogOpen(true); }}>
                                            <Plus className="h-4 w-4 mr-2" />
                                            Add User
                                        </Button>
                                    </DialogTrigger>
                                    <DialogContent>
                                        <DialogHeader>
                                            <DialogTitle>Add User</DialogTitle>
                                            <DialogDescription>
                                                Invite a new user to the organization.
                                            </DialogDescription>
                                        </DialogHeader>
                                        <form onSubmit={handleSubmitUser(handleAddUser)} className="space-y-4">
                                            <div className="space-y-2">
                                                <Label htmlFor="email">Email Address</Label>
                                                <Input id="email" type="email" placeholder="user@example.com" {...registerUser("email")} />
                                                {userErrors.email && <p className="text-sm text-destructive">{userErrors.email.message}</p>}
                                            </div>
                                            <div className="space-y-2">
                                                <Label htmlFor="role">Role</Label>
                                                <Select onValueChange={(val: "admin" | "manager" | "staff") => setValueUser("role", val)} defaultValue="staff">
                                                    <SelectTrigger>
                                                        <SelectValue placeholder="Select a role" />
                                                    </SelectTrigger>
                                                    <SelectContent>
                                                        <SelectItem value="admin">Admin</SelectItem>
                                                        <SelectItem value="manager">Manager</SelectItem>
                                                        <SelectItem value="staff">Staff</SelectItem>
                                                    </SelectContent>
                                                </Select>
                                                {/* Note: Select interaction with react-hook-form can be tricky without Controller, but simple default works for now if we bind manually or use Controller. 
                                                Let's keep it simple: Use native select or proper Controller if this was critical. 
                                                Actually, let's fix the Select binding properly using a hidden input or just native select for speed/robustness? 
                                                Better: Re-use the pattern or just use native select for the form?
                                                Let's use native select for simplicity in the hidden field or just bind the value.
                                                React Hook Form with Shadcn Select requires Controller usually.
                                                Let's switch to native <select> for "role" inside the form to avoid complex controller setup in this quick edit, 
                                                OR just use the `setValue` from `useForm` which is available.
                                            */}
                                                <div className="flex gap-2">
                                                    {['admin', 'manager', 'staff'].map(role => (
                                                        <label key={role} className="flex items-center gap-2 cursor-pointer border p-2 rounded hover:bg-muted">
                                                            <input type="radio" value={role} {...registerUser("role")} />
                                                            <span className="capitalize">{role}</span>
                                                        </label>
                                                    ))}
                                                </div>
                                                {userErrors.role && <p className="text-sm text-destructive">{userErrors.role.message}</p>}
                                            </div>

                                            <div className="space-y-2">
                                                <Label>Assign to Stores (Optional)</Label>
                                                <div className="border rounded-md p-3 space-y-2 max-h-[150px] overflow-y-auto">
                                                    {availableOrgs.length === 0 ? (
                                                        <p className="text-sm text-muted-foreground">No other stores available.</p>
                                                    ) : (
                                                        availableOrgs.map(org => (
                                                            <label key={org.id} className="flex items-center gap-2 cursor-pointer">
                                                                <input
                                                                    type="checkbox"
                                                                    value={org.id}
                                                                    {...registerUser("target_org_ids")}
                                                                    className="rounded border-gray-300 text-primary focus:ring-primary"
                                                                />
                                                                <span className="text-sm">{org.name}</span>
                                                            </label>
                                                        ))
                                                    )}
                                                </div>
                                                <p className="text-xs text-muted-foreground">
                                                    If none selected, defaults to current store only.
                                                </p>
                                            </div>

                                            <DialogFooter>
                                                <Button type="button" variant="outline" onClick={() => setIsUserDialogOpen(false)}>
                                                    Cancel
                                                </Button>
                                                <Button type="submit" disabled={loadingUsers}>
                                                    {loadingUsers && <Loader2 className="h-4 w-4 mr-2 animate-spin" />}
                                                    Send Invite
                                                </Button>
                                            </DialogFooter>
                                        </form>
                                    </DialogContent>
                                </Dialog>
                            </div>

                            {/* Edit User Dialog */}
                            <Dialog open={isEditUserOpen} onOpenChange={setIsEditUserOpen}>
                                <DialogContent>
                                    <DialogHeader>
                                        <DialogTitle>Edit User</DialogTitle>
                                        <DialogDescription>Update user details and access.</DialogDescription>
                                    </DialogHeader>
                                    <form onSubmit={handleSubmitEditUser(handleUpdateUser)} className="space-y-4">
                                        <div className="grid grid-cols-2 gap-4">
                                            <div className="space-y-2">
                                                <Label htmlFor="edit-first-name">First Name</Label>
                                                <Input id="edit-first-name" {...registerEditUser("first_name")} />
                                            </div>
                                            <div className="space-y-2">
                                                <Label htmlFor="edit-last-name">Last Name</Label>
                                                <Input id="edit-last-name" {...registerEditUser("last_name")} />
                                            </div>
                                        </div>
                                        <div className="space-y-2">
                                            <Label htmlFor="edit-email">Email</Label>
                                            <Input id="edit-email" type="email" {...registerEditUser("email")} />
                                            {editUserErrors.email && <p className="text-sm text-destructive">{editUserErrors.email.message}</p>}
                                        </div>
                                        <div className="space-y-2">
                                            <Label htmlFor="edit-role">Role</Label>
                                            <div className="flex gap-2">
                                                {['admin', 'manager', 'staff'].map(role => (
                                                    <label key={role} className="flex items-center gap-2 cursor-pointer border p-2 rounded hover:bg-muted">
                                                        <input type="radio" value={role} {...registerEditUser("role")} />
                                                        <span className="capitalize">{role}</span>
                                                    </label>
                                                ))}
                                            </div>
                                        </div>
                                        <div className="space-y-2">
                                            <Label>Assigned Stores</Label>
                                            <div className="border rounded-md p-3 space-y-2 max-h-[150px] overflow-y-auto">
                                                {availableOrgs.map(org => (
                                                    <label key={org.id} className="flex items-center gap-2 cursor-pointer">
                                                        <input
                                                            type="checkbox"
                                                            value={org.id}
                                                            {...registerEditUser("target_org_ids")}
                                                            className="rounded border-gray-300 text-primary focus:ring-primary"
                                                        />
                                                        <span className="text-sm">{org.name}</span>
                                                    </label>
                                                ))}
                                            </div>
                                            <p className="text-xs text-muted-foreground">Select stores this user can access.</p>
                                        </div>
                                        <DialogFooter>
                                            <Button type="button" variant="outline" onClick={() => setIsEditUserOpen(false)}>Cancel</Button>
                                            <Button type="submit" disabled={loadingUsers}>
                                                {loadingUsers && <Loader2 className="h-4 w-4 mr-2 animate-spin" />}
                                                Save Changes
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
                                        <TableHead>User</TableHead>
                                        <TableHead>Role</TableHead>
                                        <TableHead>Stores</TableHead>
                                        <TableHead className="text-right">Actions</TableHead>
                                    </TableRow>
                                </TableHeader>
                                <TableBody>
                                    {loadingUsers ? (
                                        <TableRow>
                                            <TableCell colSpan={4} className="text-center py-8">
                                                <Loader2 className="h-6 w-6 animate-spin mx-auto text-muted-foreground" />
                                            </TableCell>
                                        </TableRow>
                                    ) : users.length === 0 ? (
                                        <TableRow>
                                            <TableCell colSpan={4} className="text-center py-8 text-muted-foreground">
                                                No users found.
                                            </TableCell>
                                        </TableRow>
                                    ) : (
                                        users.map((u) => (
                                            <TableRow key={u.id}>
                                                <TableCell className="font-medium">
                                                    <div className="flex flex-col">
                                                        <span className="font-semibold text-gray-900">
                                                            {u.first_name || ""} {u.last_name || ""}
                                                        </span>
                                                        <span className="text-sm text-gray-500">{u.email}</span>
                                                    </div>
                                                </TableCell>
                                                <TableCell>
                                                    {u.roles.map(r => (
                                                        <span key={r} className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-blue-100 text-blue-800 capitalize">
                                                            {r}
                                                        </span>
                                                    ))}
                                                </TableCell>
                                                <TableCell>
                                                    <div className="flex flex-wrap gap-1">
                                                        {u.stores && u.stores.length > 0 ? u.stores.map(s => (
                                                            <span key={s.id} className="text-xs bg-gray-100 px-2 py-1 rounded text-gray-700">
                                                                {s.name}
                                                            </span>
                                                        )) : <span className="text-xs text-muted-foreground">None</span>}
                                                    </div>
                                                </TableCell>
                                                <TableCell className="text-right">
                                                    <div className="flex justify-end gap-2">
                                                        <Button
                                                            variant="ghost"
                                                            size="icon"
                                                            onClick={() => openEditUser(u)}
                                                        >
                                                            <Pencil className="h-4 w-4" />
                                                        </Button>
                                                        <Button
                                                            variant="ghost"
                                                            size="icon"
                                                            className="text-destructive hover:text-destructive"
                                                            onClick={() => handleDeleteUser(u.id)}
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
                    </TabsContent>
                )}
            </Tabs>
        </div>
    );
}
