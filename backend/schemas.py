from pydantic import BaseModel, validator
from typing import List, Optional, Dict
from datetime import datetime

def to_camel(string: str) -> str:
    return "".join(word.capitalize() if i > 0 else word for i, word in enumerate(string.split("_")))

class LineItemBase(BaseModel):
    sku: Optional[str] = None
    description: Optional[str] = "Unknown Item"
    units_per_case: float = 1.0
    cases: float = 0.0
    quantity: Optional[float] = 0.0
    case_cost: Optional[float] = None
    unit_cost: Optional[float] = 0.0
    amount: Optional[float] = 0.0
    category_gl_code: Optional[str] = None
    confidence_score: float = 1.0
    issue_type: Optional[str] = None # breakage, shortship, overship, misship
    issue_status: Optional[str] = "open" # open, reported, resolved, closed
    issue_description: Optional[str] = None
    issue_notes: Optional[str] = None
    
    model_config = {
        "populate_by_name": True,
        "alias_generator": to_camel
    }

class LineItemCreate(LineItemBase):
    pass

class LineItem(LineItemBase):
    id: str
    invoice_id: str

    model_config = {
        "from_attributes": True,
        "populate_by_name": True,
        "alias_generator": to_camel
    }

class InvoiceBase(BaseModel):
    invoice_number: str
    vendor_name: str
    vendor_email: Optional[str] = None
    vendor_address: Optional[str] = None
    date: Optional[str] = None
    due_date: Optional[str] = None
    total_amount: Optional[float] = 0.0
    subtotal: Optional[float] = 0.0
    shipping_amount: Optional[float] = 0.0
    discount_amount: Optional[float] = 0.0
    tax_amount: Optional[float] = 0.0
    deposit_amount: Optional[float] = 0.0
    currency: Optional[str] = "CAD"
    po_number: Optional[str] = None
    status: str
    file_url: Optional[str] = None
    issue_type: Optional[str] = None
    is_posted: bool = False

    @validator('invoice_number', 'vendor_name', pre=True, check_fields=False)
    def ensure_string(cls, v):
        return v or "UNKNOWN"

    model_config = {
        "populate_by_name": True,
        "alias_generator": to_camel
    }

class InvoiceCreate(InvoiceBase):
    pass

class InvoiceUpdate(BaseModel):
    invoice_number: Optional[str] = None
    vendor_name: Optional[str] = None
    vendor_email: Optional[str] = None
    vendor_address: Optional[str] = None
    date: Optional[str] = None
    due_date: Optional[str] = None
    total_amount: Optional[float] = None
    subtotal: Optional[float] = None
    shipping_amount: Optional[float] = None
    discount_amount: Optional[float] = None
    tax_amount: Optional[float] = None
    currency: Optional[str] = None
    po_number: Optional[str] = None
    status: Optional[str] = None
    deposit_amount: Optional[float] = None
    issue_type: Optional[str] = None
    is_posted: Optional[bool] = None
    line_items: Optional[List[LineItemBase]] = None

    class Config:
        alias_generator = to_camel
        populate_by_name = True

class Invoice(InvoiceBase):
    id: str
    created_at: datetime
    line_items: List[LineItem] = []
    category_summary: Optional[Dict[str, float]] = None

    model_config = {
        "from_attributes": True,
        "populate_by_name": True,
        "alias_generator": to_camel
    }

class InvoiceListResponse(BaseModel):
    items: List[Invoice]
    total: int
    skip: int
    limit: int

    model_config = {
        "populate_by_name": True,
        "alias_generator": to_camel
    }

class DashboardStats(BaseModel):
    total_invoices: int
    needs_review: int
    approved: int
    issue_count: int
    time_saved: str

    model_config = {
        "populate_by_name": True,
        "alias_generator": to_camel
    }

class GLCategoryBase(BaseModel):
    code: str
    name: str
    full_name: str

    model_config = {
        "populate_by_name": True,
        "alias_generator": to_camel
    }

class GLCategoryCreate(GLCategoryBase):
    pass

class GLCategory(GLCategoryBase):
    id: str
    created_at: datetime

    model_config = {
        "from_attributes": True,
        "populate_by_name": True,
        "alias_generator": to_camel
    }

# Vendor Schemas
class VendorBase(BaseModel):
    name: str
    aliases: Optional[List[str]] = None
    default_gl_category: Optional[str] = None
    notes: Optional[str] = None

class VendorCreate(VendorBase):
    pass

class VendorUpdate(BaseModel):
    name: Optional[str] = None
    aliases: Optional[List[str]] = None
    default_gl_category: Optional[str] = None
    notes: Optional[str] = None

class Vendor(VendorBase):
    id: str
    organization_id: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}

class VendorWithStats(Vendor):
    invoice_count: int = 0
    correction_count: int = 0
    last_invoice_date: Optional[str] = None
    accuracy_rate: float = 1.0

# Issue Schemas
class IssueCommunicationBase(BaseModel):
    type: str
    content: str
    recipient: Optional[str] = None

class IssueCommunicationCreate(IssueCommunicationBase):
    pass

class IssueCommunication(IssueCommunicationBase):
    id: str
    issue_id: str
    organization_id: str
    created_at: datetime
    created_by: Optional[str] = None

    model_config = {
        "from_attributes": True,
        "populate_by_name": True,
        "alias_generator": to_camel
    }

class IssueBase(BaseModel):
    type: str # breakage, shortship, overship, misship, price_mismatch
    status: str = "open"
    description: Optional[str] = None
    resolution_type: Optional[str] = None
    resolution_status: str = "pending"

class IssueCreate(IssueBase):
    invoice_id: str
    vendor_id: Optional[str] = None
    line_item_ids: List[str] = []

class IssueUpdate(BaseModel):
    type: Optional[str] = None
    status: Optional[str] = None
    description: Optional[str] = None
    resolution_type: Optional[str] = None
    resolution_status: Optional[str] = None
    resolved_at: Optional[datetime] = None

    model_config = {
        "populate_by_name": True,
        "alias_generator": to_camel
    }

class Issue(IssueBase):
    id: str
    organization_id: str
    invoice_id: str
    vendor_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    resolved_at: Optional[datetime] = None
    line_items: List[LineItem] = []
    communications: List[IssueCommunication] = []
    
    # Nested info for dashboard
    vendor_name: Optional[str] = None
    invoice_number: Optional[str] = None

    model_config = {
        "from_attributes": True,
        "populate_by_name": True,
        "alias_generator": to_camel
    }
