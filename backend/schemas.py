from pydantic import BaseModel, validator
from typing import List, Optional, Dict
from datetime import datetime

def to_camel(string: str) -> str:
    return "".join(word.capitalize() if i > 0 else word for i, word in enumerate(string.split("_")))

class LineItemBase(BaseModel):
    sku: Optional[str] = None
    description: str
    units_per_case: float = 1.0
    cases: float = 0.0
    quantity: float
    case_cost: Optional[float] = None
    unit_cost: float
    amount: float
    category_gl_code: Optional[str] = None
    confidence_score: float = 1.0
    
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
    date: str
    due_date: Optional[str] = None
    total_amount: float
    subtotal: Optional[float] = 0.0
    shipping_amount: Optional[float] = 0.0
    discount_amount: Optional[float] = 0.0
    tax_amount: float
    deposit_amount: Optional[float] = 0.0
    currency: str = "CAD"
    po_number: Optional[str] = None
    status: str
    file_url: Optional[str] = None
    issue_type: Optional[str] = None

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
