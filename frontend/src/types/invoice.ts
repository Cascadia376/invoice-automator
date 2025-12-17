export type InvoiceStatus = 'ingested' | 'parsed' | 'needs_review' | 'ready_to_push' | 'pushed' | 'failed' | 'approved';

export interface LineItem {
  id: string;
  sku?: string;
  description: string;
  unitsPerCase: number;
  cases: number;
  quantity: number;
  unitCost: number;
  amount: number;
  categoryGlCode?: string;
  confidenceScore: number;
}

export interface Invoice {
  id: string;
  invoiceNumber: string;
  vendorName: string;
  vendorEmail?: string;
  vendorAddress?: string;
  date: string;
  dueDate: string;
  totalAmount: number;
  subtotal?: number;
  shippingAmount?: number;
  discountAmount?: number;
  taxAmount: number;
  depositAmount?: number;
  currency: string;
  poNumber?: string;
  status: InvoiceStatus;
  issueType?: 'breakage' | 'shortship' | 'overship' | 'misship' | null;
  lineItems: LineItem[];
  fileUrl?: string;
  createdAt: string;
  updatedAt?: string;
}

export interface GLCategory {
  id: string;
  code: string;
  name: string;
  fullName: string;
}

export interface DashboardStats {
  totalInvoices: number;
  needsReview: number;
  pushed: number;
  timeSaved: string;
}
