from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime, Table, Boolean
from sqlalchemy.orm import relationship
from database import Base
from datetime import datetime

class Invoice(Base):
    __tablename__ = "invoices"

    id = Column(String, primary_key=True, index=True)
    organization_id = Column(String, index=True, nullable=False)
    invoice_number = Column(String, index=True)
    vendor_name = Column(String, index=True)
    vendor_email = Column(String, nullable=True)
    vendor_address = Column(String, nullable=True)
    date = Column(String)
    due_date = Column(String, nullable=True)
    total_amount = Column(Float)
    subtotal = Column(Float, default=0.0)
    shipping_amount = Column(Float, default=0.0)
    discount_amount = Column(Float, default=0.0)
    tax_amount = Column(Float)
    deposit_amount = Column(Float, default=0.0)
    currency = Column(String, default="CAD")
    po_number = Column(String, nullable=True)
    status = Column(String, default="ingested")
    issue_type = Column(String, nullable=True) # breakage, shortship, overship, misship
    file_url = Column(String, nullable=True)
    raw_extraction_results = Column(String, nullable=True) # JSON string of raw Textract/LLM output
    ldb_report_url = Column(String, nullable=True) # URL/Key to the last generated LDB report
    vendor_id = Column(String, ForeignKey("vendors.id"), nullable=True)
    is_posted = Column(Boolean, default=False)
    
    # Stellar POS integration fields
    stellar_posted_at = Column(DateTime, nullable=True)
    stellar_asn_number = Column(String, nullable=True, index=True)
    stellar_response = Column(String, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)

    line_items = relationship("LineItem", back_populates="invoice", cascade="all, delete-orphan")
    issues = relationship("Issue", back_populates="invoice", cascade="all, delete-orphan")

class LineItem(Base):
    __tablename__ = "line_items"

    id = Column(String, primary_key=True, index=True)
    invoice_id = Column(String, ForeignKey("invoices.id"))
    sku = Column(String, nullable=True, index=True)
    description = Column(String)
    units_per_case = Column(Float, default=1.0)
    cases = Column(Float, default=0.0)
    quantity = Column(Float)
    case_cost = Column(Float, nullable=True)
    unit_cost = Column(Float)
    amount = Column(Float)
    category_gl_code = Column(String, nullable=True)
    confidence_score = Column(Float, default=1.0)
    issue_type = Column(String, nullable=True) # breakage, shortship, overship, misship
    issue_status = Column(String, default="open", nullable=True) # open, reported, resolved, closed
    issue_description = Column(String, nullable=True)
    issue_notes = Column(String, nullable=True)

    invoice = relationship("Invoice", back_populates="line_items")
    issues = relationship("Issue", secondary="issue_line_items", back_populates="line_items")

class GLCategory(Base):
    __tablename__ = "gl_categories"

    id = Column(String, primary_key=True, index=True)
    organization_id = Column(String, index=True, nullable=False)
    code = Column(String, index=True) # Removed unique=True constraint as it should be unique per org, not globally
    name = Column(String)
    full_name = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)

class SKUCategoryMapping(Base):
    __tablename__ = "sku_category_mappings"

    id = Column(String, primary_key=True, index=True)
    organization_id = Column(String, index=True, nullable=False)
    sku = Column(String, index=True)
    category_gl_code = Column(String)
    usage_count = Column(Integer, default=1)
    last_used = Column(DateTime, default=datetime.utcnow)

class Template(Base):
    __tablename__ = "templates"

    id = Column(String, primary_key=True, index=True)
    organization_id = Column(String, index=True, nullable=False)
    vendor_name = Column(String, index=True)
    content = Column(String) # YAML content
    created_at = Column(DateTime, default=datetime.utcnow)

class Store(Base):
    __tablename__ = "store"

    store_id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    organization_id = Column(String, nullable=True)
    access_code = Column(String, nullable=True)
    status = Column(String, default="active")
    
    # Stellar POS integration fields
    stellar_tenant = Column(String, nullable=True)
    stellar_location_id = Column(String, nullable=True)
    stellar_location_name = Column(String, nullable=True)
    stellar_enabled = Column(Boolean, default=False)

class Vendor(Base):
    """Vendor profile with learned patterns"""
    __tablename__ = "vendors"

    id = Column(String, primary_key=True, index=True)
    organization_id = Column(String, index=True, nullable=False)
    name = Column(String, nullable=False)  # Normalized vendor name
    aliases = Column(String, nullable=True)  # JSON array of alternative names
    default_gl_category = Column(String, nullable=True)
    notes = Column(String, nullable=True)
    
    # Stellar POS integration fields
    stellar_supplier_id = Column(String, nullable=True)  # UUID in Stellar system
    stellar_supplier_name = Column(String, nullable=True)  # Supplier name as registered in Stellar
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class VendorFieldMapping(Base):
    """Textract field mappings per vendor"""
    __tablename__ = "vendor_field_mappings"

    id = Column(String, primary_key=True, index=True)
    vendor_id = Column(String, ForeignKey("vendors.id"), nullable=False)
    organization_id = Column(String, index=True, nullable=False)
    field_name = Column(String, nullable=False)  # e.g., "deposit_amount"
    textract_field = Column(String, nullable=False)  # e.g., "AMOUNT_PAID"
    confidence = Column(Float, default=1.0)  # How often this mapping is correct
    usage_count = Column(Integer, default=1)
    last_used = Column(DateTime, default=datetime.utcnow)

class GlobalVendorMapping(Base):
    """Shared registry of vendor names mapped to Stellar IDs"""
    __tablename__ = "global_vendor_mappings"

    id = Column(String, primary_key=True, index=True)
    vendor_name = Column(String, unique=True, index=True, nullable=False)
    stellar_supplier_id = Column(String, nullable=False)
    stellar_supplier_name = Column(String, nullable=False)
    confidence_score = Column(Float, default=1.0)
    usage_count = Column(Integer, default=1)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class VendorCorrection(Base):
    """Track user corrections for learning"""
    __tablename__ = "vendor_corrections"

    id = Column(String, primary_key=True, index=True)
    vendor_id = Column(String, ForeignKey("vendors.id"), nullable=False)
    organization_id = Column(String, index=True, nullable=False)
    invoice_id = Column(String, ForeignKey("invoices.id"), nullable=False)
    field_name = Column(String, nullable=False)
    original_value = Column(String, nullable=True)
    corrected_value = Column(String, nullable=False)
    correction_type = Column(String, nullable=True) # wrong_value, missing, ignored
    created_by = Column(String, nullable=True) # user_id
    created_at = Column(DateTime, default=datetime.utcnow)

class SupplierInvoice(Base):
    """Stellar POS Supplier Invoice (ASN) Header"""
    __tablename__ = "supplier_invoices"

    id = Column(Integer, primary_key=True, autoincrement=True)
    invoice_id = Column(String, unique=True, index=True) # ASN Number
    supplier_name = Column(String)
    supplier_invoice_number = Column(String, index=True)
    original_po_number = Column(String, nullable=True)
    store_id = Column(Integer, nullable=True)
    store_name = Column(String, nullable=True)
    created_date = Column(DateTime, nullable=True)
    date_received = Column(DateTime, nullable=True)
    date_posted = Column(DateTime, nullable=True)
    invoice_type = Column(String, nullable=True)
    tax_rate_name = Column(String, nullable=True)
    tax_rate = Column(Float, nullable=True)
    shipping_cost = Column(Float, nullable=True)
    total_products = Column(Integer, nullable=True)
    total_units = Column(Integer, nullable=True)
    sub_total = Column(Float, nullable=True)
    total_deposits = Column(Float, nullable=True)
    total_taxes = Column(Float, nullable=True)
    non_taxable_items = Column(Float, nullable=True)
    freight_fees = Column(Float, nullable=True)
    credits_discounts = Column(Float, nullable=True)
    invoice_total = Column(Float, nullable=True)
    status = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    meta_data = Column("metadata", String, nullable=True) # JSON store

class SupplierInvoiceItem(Base):
    """Stellar POS Supplier Invoice Line Items"""
    __tablename__ = "supplier_invoice_items"

    id = Column(Integer, primary_key=True, autoincrement=True)
    invoice_id = Column(String, ForeignKey("supplier_invoices.invoice_id"), index=True)
    line_number = Column(Integer, nullable=True)
    sku = Column(String, index=True)
    product_name = Column(String)
    volume = Column(String, nullable=True)
    units_ordered = Column(Integer, nullable=True)
    received_quantity = Column(Float, nullable=True)
    inventory_fill = Column(Integer, nullable=True)
    unit_cost = Column(Float, nullable=True)
    avg_cost = Column(Float, nullable=True)
    total_cost = Column(Float, nullable=True)
    deposit_per_unit = Column(Float, nullable=True)
    total_deposits = Column(Float, nullable=True)
    taxes = Column(Float, nullable=True)
    all_in_cost = Column(Float, nullable=True)
    variance_quantity = Column(Float, nullable=True)
    invoice_date = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    meta_data = Column("metadata", String, nullable=True) # JSON store

class Product(Base):
    """Master product data for validation"""
    __tablename__ = "product"

    sku = Column(String, primary_key=True, index=True)
    name = Column("product_name", String)
    category = Column(String, nullable=True)
    units_per_case = Column(Integer, default=1)
    average_cost = Column(Float, default=0.0)
    last_cost = Column(Float, default=0.0)
    min_typical_qty = Column(Float, nullable=True)
    max_typical_qty = Column(Float, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class ProductOrder(Base):
    """Historical record of product purchases for anomaly detection"""
    __tablename__ = "product_orders"

    id = Column(String, primary_key=True, index=True)
    organization_id = Column(String, index=True, nullable=False)
    product_id = Column(String, ForeignKey("product.sku"))
    invoice_id = Column(String, ForeignKey("invoices.id"))
    quantity = Column(Float)
    unit_cost = Column(Float)
    purchased_at = Column(DateTime, default=datetime.utcnow)

# Association table for Issues and LineItems (M2M)
issue_line_items = Table(
    "issue_line_items",
    Base.metadata,
    Column("issue_id", String, ForeignKey("issues.id"), primary_key=True),
    Column("line_item_id", String, ForeignKey("line_items.id"), primary_key=True)
)

class Issue(Base):
    __tablename__ = "issues"

    id = Column(String, primary_key=True, index=True)
    organization_id = Column(String, index=True, nullable=False)
    invoice_id = Column(String, ForeignKey("invoices.id"), nullable=False)
    vendor_id = Column(String, ForeignKey("vendors.id"), nullable=True)
    
    type = Column(String) # breakage, shortship, overship, misship, price_mismatch
    status = Column(String, default="open") # open, reported, resolved, closed
    description = Column(String, nullable=True)
    
    # Resolution details
    resolution_type = Column(String, nullable=True) # credit, replacement, refund, ignored
    resolution_status = Column(String, default="pending") # pending, completed
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    resolved_at = Column(DateTime, nullable=True)

    invoice = relationship("Invoice", back_populates="issues")
    line_items = relationship("LineItem", secondary=issue_line_items, back_populates="issues")
    communications = relationship("IssueCommunication", back_populates="issue", cascade="all, delete-orphan")

class IssueCommunication(Base):
    __tablename__ = "issue_communications"

    id = Column(String, primary_key=True, index=True)
    issue_id = Column(String, ForeignKey("issues.id"), nullable=False)
    organization_id = Column(String, index=True, nullable=False)
    
    type = Column(String) # email, note, phone_call
    content = Column(String)
    recipient = Column(String, nullable=True) # email address or contact name
    
    created_at = Column(DateTime, default=datetime.utcnow)
    created_by = Column(String, nullable=True) # user_id

    issue = relationship("Issue", back_populates="communications")

class Role(Base):
    __tablename__ = "roles"

    id = Column(String, primary_key=True, index=True) # e.g. "admin", "manager", "staff"
    name = Column(String)
    description = Column(String, nullable=True)

class UserRole(Base):
    __tablename__ = "user_roles"

    user_id = Column(String, primary_key=True, index=True)
    role_id = Column(String, ForeignKey("roles.id"), primary_key=True)
    organization_id = Column(String, primary_key=True, index=True) # Roles are org-specific
    
    created_at = Column(DateTime, default=datetime.utcnow)

class Job(Base):
    __tablename__ = "jobs"

    id = Column(String, primary_key=True, index=True)
    type = Column(String, index=True)
    status = Column(String, default="pending", index=True) # pending, running, completed, failed
    payload = Column(String, nullable=True) # JSON payload
    result = Column(String, nullable=True) # JSON result
    error = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)

class StellarSupplier(Base):
    __tablename__ = "stellar_suppliers"

    id = Column(String, primary_key=True, index=True) # Stellar UUID
    tenant_id = Column(String, index=True, nullable=False)
    name = Column(String, index=True)
    code = Column(String, nullable=True) # Supplier Code if available
    
    data = Column(String, nullable=True) # Full JSON dump for future use
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
