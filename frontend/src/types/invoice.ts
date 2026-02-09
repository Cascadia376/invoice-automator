export type InvoiceStatus = 'ingested' | 'parsed' | 'needs_review' | 'ready_to_push' | 'pushed' | 'failed' | 'approved' | 'posted';

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
  issues?: Issue[];
}

export interface Invoice {
  id: string;
  invoiceNumber: string;
  vendorName: string;
  vendorEmail?: string;
  vendorAddress?: string;
  date: string;
  dueDate?: string;
  totalAmount: number;
  subtotal?: number;
  shippingAmount?: number;
  discountAmount?: number;
  taxAmount: number;
  depositAmount?: number;
  currency: string;
  poNumber?: string;
  isPosted: boolean;
  stellarPostedAt?: string;
  stellarAsnNumber?: string;
  stellarResponse?: string;
  stellarTenant?: string;
  status: InvoiceStatus;
  lineItems: LineItem[];
  issues?: Issue[];
  fileUrl?: string;
  createdAt: string;
  updatedAt?: string;
}

export interface Issue {
  id: string;
  organizationId: string;
  invoiceId: string;
  vendorId?: string;
  type: 'breakage' | 'shortship' | 'overship' | 'misship' | 'price_mismatch';
  status: 'open' | 'reported' | 'resolved' | 'closed';
  description?: string;
  resolutionType?: 'credit' | 'replacement' | 'refund' | 'ignored';
  resolutionStatus: 'pending' | 'completed';
  createdAt: string;
  updatedAt: string;
  resolvedAt?: string;
  lineItems?: LineItem[];
  communications?: IssueCommunication[];

  // Enriched fields
  vendorName?: string;
  invoiceNumber?: string;
}

export interface IssueCommunication {
  id: string;
  issueId: string;
  organizationId: string;
  type: 'email' | 'note' | 'phone_call';
  content: string;
  recipient?: string;
  createdAt: string;
  createdBy?: string;
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
  approved: number;
  issueCount: number;
  timeSaved: string;
}

export interface PreflightIssue {
  invoiceId: string;
  issueType: 'blocking' | 'warning';
  message: string;
  actionRequired?: string;
}

export interface VendorResolutionInfo {
  invoiceIds: string[];
  vendorName: string;
  message: string;
}

export interface PreflightResponse {
  readyIds: string[];
  issues: PreflightIssue[];
  blockingVendors: VendorResolutionInfo[];
}

export interface BulkPostResult {
  success: { id: string; asn: string }[];
  failed: { id: string; reason: string }[];
}
