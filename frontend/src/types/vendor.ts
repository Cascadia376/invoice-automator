export interface Vendor {
    id: string;
    organizationId: string;
    name: string;
    aliases?: string[];
    defaultGlCategory?: string;
    notes?: string;
    createdAt: string;
    updatedAt: string;
    invoiceCount?: number;
    correctionCount?: number;
    lastInvoiceDate?: string;
    accuracyRate?: number;
    stellarSupplierId?: string;
    stellarSupplierName?: string;
}

export interface VendorCorrection {
    id: string;
    vendorId: string;
    organizationId: string;
    invoiceId: string;
    fieldName: string;
    originalValue?: string;
    correctedValue?: string;
    correctionType: string;
    rule?: string;
    createdAt: string;
    createdBy?: string;
}

export interface GlobalVendorMapping {
    id: string;
    vendorName: string;
    stellarSupplierId: string;
    stellarSupplierName: string;
    confidenceScore: number;
    usageCount: number;
}
