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
}

export interface VendorCorrection {
    id: string;
    fieldName: string;
    originalValue: string;
    correctedValue: string;
    correctionType: string;
    rule?: string;
    createdAt: string;
    createdBy?: string;
}
