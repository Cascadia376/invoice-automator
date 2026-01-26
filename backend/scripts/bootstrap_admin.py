import os
import sys
import requests

SUPABASE_URL = (os.getenv("SUPABASE_URL") or "").rstrip("/")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

def _headers():
    if not SUPABASE_URL or not SUPABASE_SERVICE_ROLE_KEY:
        raise RuntimeError("Missing SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY")
    return {
        "Authorization": f"Bearer {SUPABASE_SERVICE_ROLE_KEY}",
        "apikey": SUPABASE_SERVICE_ROLE_KEY
    }

def find_user_by_email(email: str):
    page = 1
    while True:
        resp = requests.get(
            f"{SUPABASE_URL}/auth/v1/admin/users",
            headers=_headers(),
            params={"page": page, "per_page": 200}
        )
        resp.raise_for_status()
        payload = resp.json() or {}
        users = payload.get("users", payload)
        for user in users:
            if user.get("email") == email:
                return user
        if len(users) < 200:
            break
        page += 1
    return None

def set_admin(user_id: str, org_id: str | None):
    url = f"{SUPABASE_URL}/auth/v1/admin/users/{user_id}"
    existing = requests.get(url, headers=_headers())
    existing.raise_for_status()
    user = existing.json()
    app_metadata = user.get("app_metadata", {}) or {}
    app_metadata["invoice_role"] = "admin"
    if org_id and "org_id" not in app_metadata and "organization_id" not in app_metadata:
        app_metadata["org_id"] = org_id

    update = requests.put(
        url,
        headers={**_headers(), "Content-Type": "application/json"},
        json={"app_metadata": app_metadata}
    )
    update.raise_for_status()
    return update.json()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python backend/scripts/bootstrap_admin.py user@example.com [org_id]")
        sys.exit(1)

    email = sys.argv[1]
    org_id = sys.argv[2] if len(sys.argv) > 2 else None

    user = find_user_by_email(email)
    if not user:
        print(f"User not found: {email}")
        sys.exit(2)

    updated = set_admin(user.get("id"), org_id)
    print(f"Admin role set for {email} ({updated.get('id')})")
