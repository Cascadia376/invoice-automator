import os
import stripe
from fastapi import APIRouter, Depends, HTTPException, Request, Header
from sqlalchemy.orm import Session
from database import get_db
import models
import auth
from pydantic import BaseModel

router = APIRouter()

stripe.api_key = os.getenv("STRIPE_SECRET_KEY")
endpoint_secret = os.getenv("STRIPE_WEBHOOK_SECRET")

class CheckoutSessionRequest(BaseModel):
    price_id: str

@router.post("/create-checkout-session")
async def create_checkout_session(
    request: CheckoutSessionRequest,
    ctx: auth.UserContext = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    if not stripe.api_key:
        raise HTTPException(status_code=500, detail="Stripe not configured")

    # Get or create organization record
    org = db.query(models.Organization).filter(models.Organization.id == ctx.org_id).first()
    if not org:
        # Create org record if it doesn't exist (lazy creation)
        org = models.Organization(id=ctx.org_id, name=f"Org {ctx.org_id}")
        db.add(org)
        db.commit()
        db.refresh(org)

    customer_id = org.stripe_customer_id

    try:
        # Create customer if not exists
        if not customer_id:
            customer = stripe.Customer.create(
                metadata={"org_id": ctx.org_id}
            )
            customer_id = customer.id
            org.stripe_customer_id = customer_id
            db.commit()

        checkout_session = stripe.checkout.Session.create(
            customer=customer_id,
            line_items=[
                {
                    'price': request.price_id,
                    'quantity': 1,
                },
            ],
            mode='subscription',
            success_url=os.getenv("FRONTEND_URL", "http://localhost:5173") + '/settings?success=true',
            cancel_url=os.getenv("FRONTEND_URL", "http://localhost:5173") + '/settings?canceled=true',
            metadata={"org_id": ctx.org_id}
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    return {"url": checkout_session.url}

@router.post("/webhook")
async def webhook(request: Request, stripe_signature: str = Header(None), db: Session = Depends(get_db)):
    payload = await request.body()
    event = None

    try:
        event = stripe.Webhook.construct_event(
            payload, stripe_signature, endpoint_secret
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail="Invalid payload")
    except stripe.error.SignatureVerificationError as e:
        raise HTTPException(status_code=400, detail="Invalid signature")

    # Handle the event
    if event['type'] == 'checkout.session.completed':
        session = event['data']['object']
        org_id = session.get('metadata', {}).get('org_id')
        
        if org_id:
            org = db.query(models.Organization).filter(models.Organization.id == org_id).first()
            if org:
                org.subscription_status = "active"
                db.commit()
                print(f"Organization {org_id} subscription activated.")

    elif event['type'] == 'customer.subscription.deleted':
        subscription = event['data']['object']
        # We need to find the org by customer id since metadata might not be on subscription object directly 
        # (though usually it copies from customer if set up right, but safer to look up by customer_id)
        customer_id = subscription.get('customer')
        if customer_id:
            org = db.query(models.Organization).filter(models.Organization.stripe_customer_id == customer_id).first()
            if org:
                org.subscription_status = "past_due" # or free
                db.commit()
                print(f"Organization {org.id} subscription cancelled.")

    return {"status": "success"}
