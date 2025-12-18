import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import * as z from "zod";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card } from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Trash2, Plus, ArrowUp, Settings2 } from "lucide-react";
import {
  DropdownMenu,
  DropdownMenuCheckboxItem,
  DropdownMenuContent,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Invoice } from "@/types/invoice";
import { useEffect, useMemo, useState } from "react";
import { useInvoice } from "@/context/InvoiceContext";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { cn } from "@/lib/utils";

const lineItemSchema = z.object({
  sku: z.string().optional(),
  description: z.string().min(1, "Description required"),
  unitsPerCase: z.coerce.number().min(0).default(1),
  cases: z.coerce.number().min(0).default(0),
  quantity: z.coerce.number().min(0, "Quantity must be positive"),
  unitCost: z.coerce.number().min(0, "Unit cost must be positive"),
  amount: z.coerce.number().min(0, "Amount must be positive"),
  categoryGlCode: z.string().optional(),
  confidenceScore: z.number().default(1.0),
});

const invoiceSchema = z.object({
  invoiceNumber: z.string().min(1, "Invoice number required"),
  date: z.string().min(1, "Date required"),
  dueDate: z.string().min(1, "Due date required"),
  vendorName: z.string().min(1, "Vendor name required"),
  vendorAddress: z.string().optional(),
  vendorEmail: z.string().email("Invalid email").optional().or(z.literal('')),
  poNumber: z.string().optional(),
  subtotal: z.coerce.number().min(0).optional(),
  shippingAmount: z.coerce.number().min(0).optional(),
  discountAmount: z.coerce.number().min(0).optional(),
  taxAmount: z.coerce.number().min(0),
  depositAmount: z.coerce.number().min(0).optional(),
  totalAmount: z.coerce.number().min(0, "Total required"),
  currency: z.string().min(1, "Currency required"),
  issueType: z.enum(['breakage', 'shortship', 'overship', 'misship']).nullable().optional(),
  lineItems: z.array(lineItemSchema),
});

export type InvoiceFormData = z.infer<typeof invoiceSchema>;

interface InvoiceDataEditorProps {
  data: Invoice;
  onChange: (data: Partial<Invoice>) => void;
  onFieldFocus?: (field: string | null) => void;
  validation?: {
    global_warnings: string[];
    line_item_warnings: Record<string, string[]>;
  };
}

const AVAILABLE_COLUMNS = [
  { id: "sku", label: "SKU" },
  { id: "description", label: "Description" },
  { id: "unitsPerCase", label: "Units/Case" },
  { id: "cases", label: "Cases" },
  { id: "quantity", label: "Qty" },
  { id: "unitCost", label: "Unit Cost" },
  { id: "amount", label: "Total" },
  { id: "categoryGlCode", label: "Category/GL" },
];

export function InvoiceDataEditor({ data, onChange, onFieldFocus, validation }: InvoiceDataEditorProps) {
  const { glCategories } = useInvoice();
  const safeLineItems = data.lineItems || [];

  // ... (rest of existing state)

  // Helper
  const handleInputFocus = (name: string) => {
    onFieldFocus?.(name);
  };

  const handleBlur = () => {
    // Optional: clear focus after short delay? 
    // Usually better to keep highlight while field is active
    // onFieldFocus?.(null); 
  };

  // ... (useForm setup)

  // ... (render)

  // I will use MultiReplace to inject onFocus={...} into Inputs.
  // Wait, replace_file_content on a large file is risky for "all inputs".
  // I should do it in chunks or use multi_replace carefully.
  // There are many inputs.

  // Actually, I can wrap the Input component or just add it to the specific blocks.
  // Let's look at the structure. It's grouped.

  // To avoid massive replace, I will try to target specific sections.
  // But wait, I can just use a global event listener/bubbling?
  // No, React events.

  // Let's just update the main Invoice Details Inputs first.

  // ...
  // Column Visibility State
  const [visibleColumns, setVisibleColumns] = useState<string[]>(() => {
    if (typeof window !== 'undefined') {
      const saved = localStorage.getItem("invoice-editor-columns");
      if (saved) return JSON.parse(saved);
    }
    return ["sku", "description", "unitsPerCase", "cases", "quantity", "unitCost", "amount", "categoryGlCode"];
  });

  const toggleColumn = (columnId: string) => {
    setVisibleColumns(prev => {
      const next = prev.includes(columnId)
        ? prev.filter(c => c !== columnId)
        : [...prev, columnId];
      localStorage.setItem("invoice-editor-columns", JSON.stringify(next));
      return next;
    });
  };
  const {
    register,
    watch,
    setValue,
    reset,
    formState: { errors },
  } = useForm<InvoiceFormData>({
    resolver: zodResolver(invoiceSchema),
    defaultValues: {
      invoiceNumber: data.invoiceNumber,
      date: data.date,
      dueDate: data.dueDate,
      vendorName: data.vendorName,
      vendorAddress: data.vendorAddress || '',
      vendorEmail: data.vendorEmail || '',
      poNumber: data.poNumber || '',
      subtotal: data.subtotal || 0,
      shippingAmount: data.shippingAmount || 0,
      discountAmount: data.discountAmount || 0,
      taxAmount: data.taxAmount,
      depositAmount: data.depositAmount || 0,
      totalAmount: data.totalAmount,
      currency: data.currency,
      issueType: data.issueType || null,
      lineItems: (data.lineItems || []).map(item => ({
        sku: item.sku || '',
        description: item.description,
        unitsPerCase: item.unitsPerCase || 1,
        cases: item.cases || 0,
        quantity: item.quantity,
        unitCost: item.unitCost,
        amount: item.amount,
        categoryGlCode: item.categoryGlCode || '',
        confidenceScore: item.confidenceScore || 1.0
      }))
    },
  });

  // Update form when data changes externally
  useEffect(() => {
    reset({
      invoiceNumber: data.invoiceNumber,
      date: data.date,
      dueDate: data.dueDate,
      vendorName: data.vendorName,
      vendorAddress: data.vendorAddress || '',
      vendorEmail: data.vendorEmail || '',
      poNumber: data.poNumber || '',
      subtotal: data.subtotal || 0,
      shippingAmount: data.shippingAmount || 0,
      discountAmount: data.discountAmount || 0,
      taxAmount: data.taxAmount,
      depositAmount: data.depositAmount || 0,
      totalAmount: data.totalAmount,
      currency: data.currency,
      issueType: data.issueType || null,
      lineItems: (data.lineItems || []).map(item => ({
        sku: item.sku || '',
        description: item.description,
        unitsPerCase: item.unitsPerCase || 1,
        cases: item.cases || 0,
        quantity: item.quantity,
        unitCost: item.unitCost,
        amount: item.amount,
        categoryGlCode: item.categoryGlCode || '',
        confidenceScore: item.confidenceScore || 1.0
      }))
    });
  }, [data.id, reset]);

  const lineItems = watch("lineItems");

  const addLineItem = () => {
    const newItems = [
      ...lineItems,
      {
        sku: "",
        description: "",
        unitsPerCase: 1,
        cases: 0,
        quantity: 0,
        unitCost: 0,
        amount: 0,
        categoryGlCode: "",
        confidenceScore: 1.0
      },
    ];
    setValue("lineItems", newItems);
    handleFieldChange();
  };

  const removeLineItem = (index: number) => {
    const newItems = lineItems.filter((_, i) => i !== index);
    setValue("lineItems", newItems);
    handleFieldChange();
  };

  const handleFieldChange = () => {
    const formData = watch();
    onChange({
      ...formData,
      lineItems: formData.lineItems.map((item, idx) => ({
        id: safeLineItems[idx]?.id || Math.random().toString(36).substr(2, 9),
        sku: item.sku,
        description: item.description || '',
        unitsPerCase: item.unitsPerCase || 1,
        cases: item.cases || 0,
        quantity: item.quantity || 0,
        unitCost: item.unitCost || 0,
        amount: item.amount || 0,
        categoryGlCode: item.categoryGlCode,
        confidenceScore: item.confidenceScore || 1.0
      }))
    });
  };

  // Calculate Category Totals
  const categoryTotals = useMemo(() => {
    const totals: Record<string, number> = {};
    lineItems.forEach(item => {
      const category = item.categoryGlCode || "Uncategorized";
      totals[category] = (totals[category] || 0) + (item.amount || 0);
    });
    return Object.entries(totals).sort((a, b) => b[1] - a[1]);
  }, [lineItems]);

  // Validation Logic
  const subtotal = watch("subtotal") || 0;
  const tax = watch("taxAmount") || 0;
  const shipping = watch("shippingAmount") || 0;
  const discount = watch("discountAmount") || 0;
  const deposit = watch("depositAmount") || 0;
  const total = watch("totalAmount") || 0;

  const calculatedTotal = subtotal + tax + shipping + deposit - discount;
  const totalMismatch = Math.abs(calculatedTotal - total) > 0.05;

  const lineItemsSum = lineItems.reduce((sum, item) => sum + (item.amount || 0), 0);
  const subtotalMismatch = Math.abs(lineItemsSum - subtotal) > 0.05;

  const getConfidenceColor = (score: number) => {
    if (score <= 0.4) return "bg-red-50 hover:bg-red-100 border-l-2 border-l-red-500";
    if (score <= 0.8) return "bg-yellow-50 hover:bg-yellow-100 border-l-2 border-l-yellow-500";
    return "";
  };

  return (
    <Card className="h-full flex flex-col bg-card">
      <div className="border-b border-border/40 p-3 flex justify-between items-center bg-muted/20">
        <div>
          <h2 className="text-lg font-semibold flex items-center gap-2">
            Extracted Data
            {(totalMismatch || subtotalMismatch) && (
              <span className="flex h-2 w-2 rounded-full bg-red-500 animate-pulse" />
            )}
          </h2>
          <p className="text-xs text-muted-foreground">Review and edit invoice details</p>
        </div>

        {/* Global Validation Warnings */}
        <div className="flex gap-2">
          {totalMismatch && (
            <div className="text-xs px-2 py-1 bg-red-100 text-red-700 rounded-md border border-red-200 flex items-center gap-1">
              <span className="material-symbols-outlined text-sm">warning</span>
              Check Total
            </div>
          )}
          {subtotalMismatch && (
            <div className="text-xs px-2 py-1 bg-yellow-100 text-yellow-700 rounded-md border border-yellow-200 flex items-center gap-1">
              <span className="material-symbols-outlined text-sm">calculate</span>
              Check Lines
            </div>
          )}
        </div>
      </div>

      {/* Smart Validation Global Warnings */}
      {
        validation?.global_warnings && validation.global_warnings.length > 0 && (
          <div className="bg-orange-50 border-b border-orange-100 p-2 text-xs text-orange-800 flex flex-col gap-1">
            {validation.global_warnings.map((w, i) => (
              <div key={i} className="flex items-center gap-2">
                <span className="material-symbols-outlined text-sm font-bold">warning</span>
                <span className="font-medium">{w}</span>
              </div>
            ))}
          </div>
        )
      }

      <ScrollArea className="flex-1 p-4">
        <form className="space-y-6" onChange={handleFieldChange}>
          {/* Invoice & Vendor Details - Split View */}
          <div className="grid grid-cols-2 gap-6">
            {/* Left Column: Invoice Details */}
            <div className="space-y-3">
              <h3 className="text-xs font-medium text-muted-foreground uppercase tracking-wider">Invoice Details</h3>
              <div className="grid grid-cols-2 gap-3">
                <div className="col-span-2">
                  <Label htmlFor="invoiceNumber" className="text-xs">Invoice Number</Label>
                  <Input
                    id="invoiceNumber"
                    {...register("invoiceNumber")}
                    className={cn("mt-1 h-8 text-sm", !watch("invoiceNumber") && "border-red-300 bg-red-50")}
                    onFocus={() => onFieldFocus?.("invoiceNumber")}
                  />
                  {errors.invoiceNumber && <p className="text-xs text-destructive mt-1">{errors.invoiceNumber.message}</p>}
                </div>
                <div>
                  <Label htmlFor="date" className="text-xs">Issue Date</Label>
                  <Input
                    id="date"
                    type="date"
                    {...register("date")}
                    className={cn("mt-1 h-8 text-sm", !watch("date") && "border-red-300 bg-red-50")}
                    onFocus={() => onFieldFocus?.("date")}
                  />
                </div>
                <div>
                  <Label htmlFor="dueDate" className="text-xs">Due Date</Label>
                  <Input id="dueDate" type="date" {...register("dueDate")} className="mt-1 h-8 text-sm" onFocus={() => onFieldFocus?.("dueDate")} />
                </div>
                <div>
                  <Label htmlFor="poNumber" className="text-xs">PO Number</Label>
                  <Input id="poNumber" {...register("poNumber")} className="mt-1 h-8 text-sm" />
                </div>
                <div>
                  {/* Currency hidden as it is always CAD */}
                </div>
                <div className="col-span-2">
                  <Label htmlFor="issueType" className="text-xs">Invoice Issue (if any)</Label>
                  <select
                    id="issueType"
                    {...register("issueType")}
                    className="mt-1 block w-full rounded-md border border-input bg-background px-3 py-1.5 text-sm ring-offset-background focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
                  >
                    <option value="">No Issue</option>
                    <option value="breakage">Breakage</option>
                    <option value="shortship">Shortship</option>
                    <option value="overship">Overship</option>
                    <option value="misship">Mis-ship</option>
                  </select>
                </div>
              </div>
            </div>

            {/* Right Column: Vendor Details */}
            <div className="space-y-3">
              <h3 className="text-xs font-medium text-muted-foreground uppercase tracking-wider">Vendor Details</h3>
              <div className="space-y-3">
                <div>
                  <Label htmlFor="vendorName" className="text-xs">Vendor Name</Label>
                  <Input
                    id="vendorName"
                    {...register("vendorName")}
                    className={cn("mt-1 h-8 text-sm", !watch("vendorName") && "border-red-300 bg-red-50")}
                    onFocus={() => onFieldFocus?.("vendorName")}
                  />
                </div>
                <div>
                  <Label htmlFor="vendorAddress" className="text-xs">Address</Label>
                  <Input id="vendorAddress" {...register("vendorAddress")} className="mt-1 h-8 text-sm" />
                </div>
                <div>
                  <Label htmlFor="vendorEmail" className="text-xs">Email</Label>
                  <Input id="vendorEmail" type="email" {...register("vendorEmail")} className="mt-1 h-8 text-sm" />
                </div>
              </div>
            </div>
          </div>

          <Separator />

          {/* Line Items Table */}
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <h3 className="text-sm font-semibold">Line Items</h3>

              <div className="flex items-center gap-4">
                {subtotalMismatch && (
                  <span className="text-xs text-yellow-600">
                    Sum ({lineItemsSum.toFixed(2)}) ≠ Subtotal ({subtotal.toFixed(2)})
                  </span>
                )}

                <DropdownMenu>
                  <DropdownMenuTrigger asChild>
                    <Button variant="outline" size="sm" className="h-7 text-xs gap-1">
                      <Settings2 className="h-3.5 w-3.5" />
                      Columns
                    </Button>
                  </DropdownMenuTrigger>
                  <DropdownMenuContent align="end" className="w-48">
                    <DropdownMenuLabel>Toggle Columns</DropdownMenuLabel>
                    <DropdownMenuSeparator />
                    {AVAILABLE_COLUMNS.map((col) => (
                      <DropdownMenuCheckboxItem
                        key={col.id}
                        checked={visibleColumns.includes(col.id)}
                        onCheckedChange={() => toggleColumn(col.id)}
                      >
                        {col.label}
                      </DropdownMenuCheckboxItem>
                    ))}
                  </DropdownMenuContent>
                </DropdownMenu>
              </div>
            </div>

            <div className="border rounded-md overflow-x-auto">
              <Table className="min-w-[1000px]">
                <TableHeader>
                  <TableRow className="bg-muted/50 h-9">
                    <TableHead className="w-[40px] h-9 py-1 text-xs text-center">#</TableHead>

                    {visibleColumns.includes('sku') && (
                      <TableHead className="min-w-[100px] h-9 py-1 text-xs">SKU</TableHead>
                    )}
                    {visibleColumns.includes('description') && (
                      <TableHead className="min-w-[200px] h-9 py-1 text-xs">Description</TableHead>
                    )}
                    {visibleColumns.includes('unitsPerCase') && (
                      <TableHead className="min-w-[80px] text-right h-9 py-1 text-xs">Units/Case</TableHead>
                    )}
                    {visibleColumns.includes('cases') && (
                      <TableHead className="min-w-[80px] text-right h-9 py-1 text-xs">Cases</TableHead>
                    )}
                    {visibleColumns.includes('quantity') && (
                      <TableHead className="min-w-[80px] text-right h-9 py-1 text-xs">Qty</TableHead>
                    )}
                    {visibleColumns.includes('unitCost') && (
                      <TableHead className="min-w-[100px] text-right h-9 py-1 text-xs">Unit Cost</TableHead>
                    )}
                    {visibleColumns.includes('amount') && (
                      <TableHead className="min-w-[100px] text-right h-9 py-1 text-xs">Total</TableHead>
                    )}
                    {visibleColumns.includes('categoryGlCode') && (
                      <TableHead className="min-w-[150px] h-9 py-1 text-xs">Category/GL</TableHead>
                    )}

                    <TableHead className="w-[50px] h-9 py-1"></TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {lineItems.map((item, index) => (
                    <TableRow key={index} className={cn("h-10 transition-colors", getConfidenceColor(item.confidenceScore))}>
                      <TableCell className="p-1 text-center text-xs text-muted-foreground relative group">
                        {index + 1}
                        {item.confidenceScore < 0.8 && (
                          <div className="absolute left-0 top-0 h-full w-1 bg-transparent group-hover:bg-yellow-400" title={`Confidence: ${(item.confidenceScore * 100).toFixed(0)}%`} />
                        )}
                        {/* Validation Warning Marker */}
                        {validation?.line_item_warnings && safeLineItems[index]?.id && validation.line_item_warnings[safeLineItems[index].id] && (
                          <div
                            className="absolute right-0 top-1/2 -translate-y-1/2 translate-x-1/2 text-orange-500 cursor-help z-10 bg-white rounded-full shadow-sm"
                            title={validation.line_item_warnings[safeLineItems[index].id].join('\n')}
                          >
                            <span className="material-symbols-outlined text-sm leading-none block">warning</span>
                          </div>
                        )}
                      </TableCell>
                      {visibleColumns.includes('sku') && (
                        <TableCell className="p-1">
                          <Input
                            {...register(`lineItems.${index}.sku`)}
                            className="h-7 w-full bg-transparent border-transparent hover:border-input focus:border-input px-2 text-xs"
                            placeholder="SKU"
                          />
                        </TableCell>
                      )}
                      {visibleColumns.includes('description') && (
                        <TableCell className="p-1">
                          <Input
                            {...register(`lineItems.${index}.description`)}
                            className="h-7 w-full bg-transparent border-transparent hover:border-input focus:border-input px-2 text-xs"
                          />
                        </TableCell>
                      )}
                      {visibleColumns.includes('unitsPerCase') && (
                        <TableCell className="p-1">
                          <Input
                            type="number"
                            {...register(`lineItems.${index}.unitsPerCase`)}
                            className="h-7 w-full bg-transparent border-transparent hover:border-input focus:border-input px-2 text-right text-xs"
                          />
                        </TableCell>
                      )}
                      {visibleColumns.includes('cases') && (
                        <TableCell className="p-1">
                          <Input
                            type="number"
                            {...register(`lineItems.${index}.cases`)}
                            className="h-7 w-full bg-transparent border-transparent hover:border-input focus:border-input px-2 text-right text-xs"
                          />
                        </TableCell>
                      )}
                      {visibleColumns.includes('quantity') && (
                        <TableCell className="p-1">
                          <Input
                            type="number"
                            {...register(`lineItems.${index}.quantity`)}
                            className="h-7 w-full bg-transparent border-transparent hover:border-input focus:border-input px-2 text-right text-xs"
                          />
                        </TableCell>
                      )}
                      {visibleColumns.includes('unitCost') && (
                        <TableCell className="p-1">
                          <Input
                            type="number"
                            step="0.01"
                            {...register(`lineItems.${index}.unitCost`)}
                            className="h-7 w-full bg-transparent border-transparent hover:border-input focus:border-input px-2 text-right text-xs"
                          />
                        </TableCell>
                      )}
                      {visibleColumns.includes('amount') && (
                        <TableCell className="p-1">
                          <Input
                            type="number"
                            step="0.01"
                            {...register(`lineItems.${index}.amount`)}
                            className="h-7 w-full bg-transparent border-transparent hover:border-input focus:border-input px-2 text-right font-medium text-xs"
                            onFocus={() => onFieldFocus?.(`lineItems[${index}].amount`)}
                          />
                        </TableCell>
                      )}
                      {visibleColumns.includes('categoryGlCode') && (
                        <TableCell className="p-1">
                          <Input
                            {...register(`lineItems.${index}.categoryGlCode`)}
                            className="h-7 w-full bg-transparent border-transparent hover:border-input focus:border-input px-2 text-xs"
                            placeholder="Select..."
                            list="gl-categories"
                          />
                        </TableCell>
                      )}
                      <TableCell className="p-1">
                        <Button
                          type="button"
                          variant="ghost"
                          size="icon"
                          className="h-7 w-7 text-muted-foreground hover:text-destructive"
                          onClick={() => removeLineItem(index)}
                        >
                          <Trash2 className="h-3 w-3" />
                        </Button>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
              <datalist id="gl-categories">
                {glCategories.map((category) => (
                  <option key={category.id} value={category.code}>
                    {category.fullName}
                  </option>
                ))}
              </datalist>
            </div>
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={addLineItem}
              className="w-full border-dashed h-8 text-xs"
            >
              <Plus className="h-3 w-3 mr-2" />
              Add New Line Item
            </Button>
          </div>

          {/* Category Totals */}
          <div className="space-y-3">
            <h3 className="text-sm font-semibold">Category/GL Code Totals</h3>
            <div className="border rounded-md overflow-hidden">
              <Table>
                <TableHeader>
                  <TableRow className="bg-muted/50 h-8">
                    <TableHead className="h-8 py-1 text-xs">Category/GL Code</TableHead>
                    <TableHead className="text-right h-8 py-1 text-xs">Subtotal</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {categoryTotals.map(([category, total]) => (
                    <TableRow key={category} className="h-8">
                      <TableCell className="font-medium p-2 text-xs">{category}</TableCell>
                      <TableCell className="text-right font-mono p-2 text-xs">${total.toFixed(2)}</TableCell>
                    </TableRow>
                  ))}
                  {categoryTotals.length === 0 && (
                    <TableRow>
                      <TableCell colSpan={2} className="text-center text-muted-foreground py-2 text-xs">
                        No line items with categories
                      </TableCell>
                    </TableRow>
                  )}
                </TableBody>
              </Table>
            </div>
          </div>

          <Separator />

          {/* Invoice Totals */}
          <div className="flex justify-end">
            <div className="w-64 space-y-2">
              <div className="flex justify-between items-center">
                <Label htmlFor="subtotal" className="text-xs text-muted-foreground">Subtotal</Label>
                <div className="relative">
                  <Input
                    id="subtotal"
                    type="number"
                    step="0.01"
                    {...register("subtotal")}
                    className={cn("w-28 text-right h-7 text-xs", subtotalMismatch && "border-yellow-400 bg-yellow-50")}
                  />
                </div>
              </div>
              <div className="flex justify-between items-center">
                <Label htmlFor="shippingAmount" className="text-xs text-muted-foreground">Shipping</Label>
                <Input
                  id="shippingAmount"
                  type="number"
                  step="0.01"
                  {...register("shippingAmount")}
                  className="w-28 text-right h-7 text-xs"
                  onFocus={() => onFieldFocus?.("shippingAmount")}
                />
              </div>
              <div className="flex justify-between items-center">
                <Label htmlFor="discountAmount" className="text-xs text-muted-foreground">Discount</Label>
                <Input
                  id="discountAmount"
                  type="number"
                  step="0.01"
                  {...register("discountAmount")}
                  className="w-28 text-right h-7 text-xs"
                  onFocus={() => onFieldFocus?.("discountAmount")}
                />
              </div>
              <div className="flex justify-between items-center">
                <Label htmlFor="taxAmount" className="text-xs text-muted-foreground">Tax</Label>
                <Input
                  id="taxAmount"
                  type="number"
                  step="0.01"
                  {...register("taxAmount")}
                  className="w-28 text-right h-7 text-xs"
                  onFocus={() => onFieldFocus?.("taxAmount")}
                />
              </div>
              <div className="flex justify-between items-center">
                <Label htmlFor="depositAmount" className="text-xs text-muted-foreground">Deposit</Label>
                <Input
                  id="depositAmount"
                  type="number"
                  step="0.01"
                  {...register("depositAmount")}
                  className="w-28 text-right h-7 text-xs"
                />
              </div>
              <Separator />
              <div className="flex justify-between items-center pt-1">
                <Label htmlFor="totalAmount" className="text-sm font-bold flex items-center gap-1">
                  Total
                  {totalMismatch && <span className="h-1.5 w-1.5 rounded-full bg-red-500" title="Does not match calculated total" />}
                </Label>
                <div className="relative">
                  <Input
                    id="totalAmount"
                    type="number"
                    step="0.01"
                    {...register("totalAmount")}
                    className={cn("w-28 text-right font-bold h-8 text-sm", totalMismatch && "border-red-400 bg-red-50")}
                    onFocus={() => onFieldFocus?.("totalAmount")}
                  />
                  {totalMismatch && (
                    <div className="absolute right-32 top-1 text-xs text-muted-foreground whitespace-nowrap">
                      Calc: {calculatedTotal.toFixed(2)}
                    </div>
                  )}
                </div>
              </div>
            </div>
          </div>
        </form>
      </ScrollArea>
    </Card >
  );
}
