# Stripe Payments Setup Guide

The Stripe integration has been implemented in the codebase but requires configuration to be fully active. This guide details the steps to enable payments when ready (post-beta).

## Current Status
- **Backend**: 
  - `models.Organization` has fields for `stripe_customer_id` and `subscription_status`.
  - `/api/billing/create-checkout-session` endpoint is ready.
  - `/api/billing/webhook` endpoint is ready to handle `checkout.session.completed` and `customer.subscription.deleted`.
- **Frontend**:
  - `Settings.tsx` has a "Subscription" section with an "Upgrade to Pro" button.
  - The button calls the backend to create a checkout session.

## Configuration Steps

### 1. Stripe Dashboard Setup
1.  Log in to your [Stripe Dashboard](https://dashboard.stripe.com/).
2.  **Create a Product**:
    - Go to **Products** -> **Add Product**.
    - Name: "Pro Plan" (or similar).
    - Price: Set your monthly/yearly price (e.g., $29/month).
    - **Copy the Price ID** (starts with `price_...`). You will need this for the Frontend.
3.  **Get API Keys**:
    - Go to **Developers** -> **API keys**.
    - Copy the **Secret key** (`sk_test_...` or `sk_live_...`).
4.  **Setup Webhook**:
    - Go to **Developers** -> **Webhooks** -> **Add endpoint**.
    - Endpoint URL: `https://your-backend-url.onrender.com/api/billing/webhook`
    - Events to listen for:
        - `checkout.session.completed`
        - `customer.subscription.deleted`
    - **Copy the Signing secret** (`whsec_...`).

### 2. Environment Variables
Add the following variables to your Backend environment (Render):

```env
STRIPE_SECRET_KEY=sk_test_...
STRIPE_WEBHOOK_SECRET=whsec_...
FRONTEND_URL=https://your-frontend-url.vercel.app
```

### 3. Update Frontend Code
Open `frontend/src/pages/Settings.tsx` and find the `handleUpgrade` function.

Replace the placeholder Price ID with your actual one:

```typescript
// frontend/src/pages/Settings.tsx

body: JSON.stringify({
    price_id: "price_1234567890" // <--- REPLACE THIS with your actual Stripe Price ID
})
```

### 4. Verification
1.  Deploy the changes.
2.  Log in as a user.
3.  Go to Settings -> Click "Upgrade to Pro".
4.  Complete the checkout in Stripe (use [test cards](https://stripe.com/docs/testing) if in test mode).
5.  Verify you are redirected back to Settings with a success message.
6.  Verify the Organization's `subscription_status` is updated to `active` in the database.
