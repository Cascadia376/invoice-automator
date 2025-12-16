from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime
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
    currency = Column(String, default="USD")
    po_number = Column(String, nullable=True)
    status = Column(String, default="ingested")
    file_url = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    line_items = relationship("LineItem", back_populates="invoice", cascade="all, delete-orphan")

class LineItem(Base):
    __tablename__ = "line_items"

    id = Column(String, primary_key=True, index=True)
    invoice_id = Column(String, ForeignKey("invoices.id"))
    sku = Column(String, nullable=True, index=True)
    description = Column(String)
    units_per_case = Column(Float, default=1.0)
    cases = Column(Float, default=0.0)
    quantity = Column(Float)
    unit_cost = Column(Float)
    amount = Column(Float)
    category_gl_code = Column(String, nullable=True)
    confidence_score = Column(Float, default=1.0)

    invoice = relationship("Invoice", back_populates="line_items")

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

class QBOCredentials(Base):
    __tablename__ = "qbo_credentials"

    realm_id = Column(String, primary_key=True, index=True)
    organization_id = Column(String, index=True, nullable=False)
    access_token = Column(String)
    refresh_token = Column(String)
    access_token_expires_at = Column(DateTime)
    refresh_token_expires_at = Column(DateTime)
    updated_at = Column(DateTime, default=datetime.utcnow)

class Template(Base):
    __tablename__ = "templates"

    id = Column(String, primary_key=True, index=True)
    organization_id = Column(String, index=True, nullable=False)
    vendor_name = Column(String, index=True)
    content = Column(String) # YAML content
    created_at = Column(DateTime, default=datetime.utcnow)

class Organization(Base):
    __tablename__ = "organizations"

    id = Column(String, primary_key=True, index=True)
    name = Column(String)
    stripe_customer_id = Column(String, index=True, nullable=True)
    subscription_status = Column(String, default="free") # free, active, past_due
    created_at = Column(DateTime, default=datetime.utcnow)

class Vendor(Base):
    """Vendor profile with learned patterns"""
    __tablename__ = "vendors"

    id = Column(String, primary_key=True, index=True)
    organization_id = Column(String, index=True, nullable=False)
    name = Column(String, nullable=False)  # Normalized vendor name
    aliases = Column(String, nullable=True)  # JSON array of alternative names
    default_gl_category = Column(String, nullable=True)
    notes = Column(String, nullable=True)
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

class VendorCorrection(Base):
    """Track user corrections for learning"""
    __tablename__ = "vendor_corrections"

    id = Column(String, primary_key=True, index=True)
    vendor_id = Column(String, ForeignKey("vendors.id"), nullable=False)
    organization_id = Column(String, index=True, nullable=False)
    invoice_id = Column(String, ForeignKey("invoices.id"), nullable=False)
    field_name = Column(String, nullable=False)
    original_value = Column(String, nullable=True)
    corrected_value = Column(String, nullable=True)
    correction_type = Column(String, nullable=False)  # "missing", "wrong_value", "calculation"
    rule = Column(String, nullable=True)  # e.g., "deposit = subtotal * 0.05"
    created_at = Column(DateTime, default=datetime.utcnow)
    created_by = Column(String, nullable=True)  # user_id

