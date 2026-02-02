
from fastapi import APIRouter, Depends, Query, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from datetime import datetime, date
import io

from database import get_db
from services import reports_service

router = APIRouter(
    prefix="/reports",
    tags=["reports"]
)

@router.get("/receiving-summary")
async def get_receiving_summary(
    start_date: date = Query(..., description="Start Date (YYYY-MM-DD)"),
    end_date: date = Query(..., description="End Date (YYYY-MM-DD)"),
    db: Session = Depends(get_db)
):
    """
    Download Receiving Summary Report as CSV.
    """
    # Convert dates to datetime for ensuring full coverage (start of day to end of day)
    start_dt = datetime.combine(start_date, datetime.min.time())
    end_dt = datetime.combine(end_date, datetime.max.time())
    
    csv_content = reports_service.generate_receiving_summary_csv(db, start_dt, end_dt)
    
    if not csv_content:
        raise HTTPException(status_code=404, detail="No invoices found in this date range.")
        
    response = StreamingResponse(
        io.StringIO(csv_content),
        media_type="text/csv"
    )
    
    filename = f"receiving_summary_{start_date}_{end_date}.csv"
    response.headers["Content-Disposition"] = f"attachment; filename={filename}"
    return response
