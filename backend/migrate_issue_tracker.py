
import os
import uuid
from sqlalchemy import create_engine, text
from datetime import datetime

# Get DB URL from env
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
default_db_path = os.path.join(BASE_DIR, "sql_app.db")
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{default_db_path}")

# Fix for Render's Postgres URL
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

connect_args = {"check_same_thread": False} if "sqlite" in DATABASE_URL else {}

print(f"DATABASE CONNECTION: {DATABASE_URL.split('@')[-1] if '@' in DATABASE_URL else 'sqlite_root'}")

engine = create_engine(DATABASE_URL, connect_args=connect_args)

def migrate():
    with engine.begin() as conn:
        print("Creating new tables...")
        
        # 1. Create issues table
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS issues (
                id VARCHAR PRIMARY KEY,
                organization_id VARCHAR NOT NULL,
                invoice_id VARCHAR NOT NULL,
                vendor_id VARCHAR,
                type VARCHAR,
                status VARCHAR DEFAULT 'open',
                description VARCHAR,
                resolution_type VARCHAR,
                resolution_status VARCHAR DEFAULT 'pending',
                created_at DATETIME,
                updated_at DATETIME,
                resolved_at DATETIME,
                FOREIGN KEY (invoice_id) REFERENCES invoices(id),
                FOREIGN KEY (vendor_id) REFERENCES vendors(id)
            )
        """))
        
        # 2. Create issue_communications table
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS issue_communications (
                id VARCHAR PRIMARY KEY,
                issue_id VARCHAR NOT NULL,
                organization_id VARCHAR NOT NULL,
                type VARCHAR,
                content VARCHAR,
                recipient VARCHAR,
                created_at DATETIME,
                created_by VARCHAR,
                FOREIGN KEY (issue_id) REFERENCES issues(id)
            )
        """))
        
        # 3. Create issue_line_items association table
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS issue_line_items (
                issue_id VARCHAR NOT NULL,
                line_item_id VARCHAR NOT NULL,
                PRIMARY KEY (issue_id, line_item_id),
                FOREIGN KEY (issue_id) REFERENCES issues(id),
                FOREIGN KEY (line_item_id) REFERENCES line_items(id)
            )
        """))
        
        print("Migrating existing issue data from line_items...")
        
        # Fetch line items with issues
        res = conn.execute(text("SELECT id, invoice_id, issue_type, issue_status, issue_description, issue_notes FROM line_items WHERE issue_type IS NOT NULL"))
        items_with_issues = res.fetchall()
        
        for row in items_with_issues:
            li_id, inv_id, i_type, i_status, i_desc, i_notes = row
            
            # Fetch organization_id and vendor_id from invoice
            inv_res = conn.execute(text("SELECT organization_id, vendor_id FROM invoices WHERE id = :id"), {"id": inv_id})
            inv_row = inv_res.fetchone()
            if not inv_row:
                continue
            
            org_id, vendor_id = inv_row
            
            # Create a new issue
            issue_id = str(uuid.uuid4())
            now = datetime.utcnow()
            
            conn.execute(text("""
                INSERT INTO issues (id, organization_id, invoice_id, vendor_id, type, status, description, created_at, updated_at)
                VALUES (:id, :org_id, :inv_id, :v_id, :type, :status, :desc, :now, :now)
            """), {
                "id": issue_id,
                "org_id": org_id,
                "inv_id": inv_id,
                "v_id": vendor_id,
                "type": i_type,
                "status": i_status or 'open',
                "desc": i_desc or i_notes,
                "now": now
            })
            
            # Link line item to the issue
            conn.execute(text("""
                INSERT INTO issue_line_items (issue_id, line_item_id)
                VALUES (:issue_id, :line_item_id)
            """), {
                "issue_id": issue_id,
                "line_item_id": li_id
            })

            # If there were notes, add as a communication entry
            if i_notes:
                comm_id = str(uuid.uuid4())
                conn.execute(text("""
                    INSERT INTO issue_communications (id, issue_id, organization_id, type, content, created_at)
                    VALUES (:id, :issue_id, :org_id, 'note', :content, :now)
                """), {
                    "id": comm_id,
                    "issue_id": issue_id,
                    "org_id": org_id,
                    "content": i_notes,
                    "now": now
                })
                
    print("Migration complete!")

if __name__ == "__main__":
    migrate()
