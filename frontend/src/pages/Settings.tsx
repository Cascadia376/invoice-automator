import { useState, useEffect } from "react";
import { useInvoice } from "@/context/InvoiceContext";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
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
import { Plus, Pencil, Trash2, Loader2 } from "lucide-react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import * as z from "zod";
import { GLCategory } from "@/types/invoice";

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
