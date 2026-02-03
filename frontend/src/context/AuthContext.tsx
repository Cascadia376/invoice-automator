import React, { createContext, useContext, useEffect, useState, useCallback } from "react";
import { Session, User } from "@supabase/supabase-js";
import { supabase } from "@/lib/supabaseClient";

export type Store = {
  id: string;
  name: string;
};

type AuthContextType = {
  session: Session | null;
  user: User | null;
  orgId: string | null;
  stores: Store[];
  roles: string[];
  loading: boolean;
  getToken: () => Promise<string | null>;
  signOut: () => Promise<void>;
  switchStore: (orgId: string) => void;
  disableAuth: boolean;
  isAdmin: boolean;
};

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const disableAuth = import.meta.env.VITE_DISABLE_AUTH === "true";
  const [session, setSession] = useState<Session | null>(null);
  const [user, setUser] = useState<User | null>(null);
  const [roles, setRoles] = useState<string[]>([]);
  const [stores, setStores] = useState<Store[]>([]);
  const [activeOrgId, setActiveOrgId] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  // Fetch roles from backend
  const fetchRoles = async (userId: string, orgId: string, token: string) => {
    try {
      console.log(`[AuthDebug] Fetching roles for User: ${userId}, Org: ${orgId}`);
      const res = await fetch(`${import.meta.env.VITE_API_URL || 'https://invoice-backend-a1gb.onrender.com'}/api/users/me/roles`, {
        headers: { Authorization: `Bearer ${token}`, "x-organization-id": orgId }
      });

      if (res.ok) {
        const data = await res.json();
        setRoles(data.roles || []);
      }
    } catch (e) {
      console.error("[AuthDebug] Error fetching roles", e);
    }
  };

  const fetchStores = async (token: string) => {
    try {
      console.log("[AuthDebug] Fetching stores...");
      const res = await fetch(`${import.meta.env.VITE_API_URL || 'https://invoice-backend-a1gb.onrender.com'}/api/users/me/stores`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      if (res.ok) {
        const data = await res.json();
        console.log(`[AuthDebug] Fetched ${data?.length} stores:`, data);
        setStores(data || []);
      } else {
        console.error(`[AuthDebug] Failed to fetch stores: ${res.status}`);
      }
    } catch (e) {
      console.error("[AuthDebug] Error fetching stores", e);
    }
  };

  useEffect(() => {
    const init = async () => {
      const { data } = await supabase.auth.getSession();
      setSession(data.session);
      setUser(data.session?.user ?? null);

      if (data.session?.user && data.session?.access_token) {
        // Fetch the actual org_id from the backend to ensure consistency
        try {
          const whoamiRes = await fetch(`${import.meta.env.VITE_API_URL || 'https://invoice-backend-a1gb.onrender.com'}/api/whoami`, {
            headers: { Authorization: `Bearer ${data.session.access_token}` }
          });

          if (whoamiRes.ok) {
            const whoamiData = await whoamiRes.json();
            const backendOrgId = whoamiData.claims?.org_id || whoamiData.claims?.organization_id;

            if (backendOrgId) {
              console.log(`[AuthDebug] Using backend org_id: ${backendOrgId}`);
              setActiveOrgId(backendOrgId);
              await fetchStores(data.session.access_token);
              fetchRoles(data.session.user.id, backendOrgId, data.session.access_token);
              setLoading(false);
              return;
            }
          }
        } catch (e) {
          console.error("[AuthDebug] Failed to fetch whoami, falling back to metadata", e);
        }

        // Fallback to original logic if whoami fails
        const persistedOrg = localStorage.getItem("active_org_id");
        const defaultOrg = data.session.user.user_metadata?.org_id || data.session.user.id;
        const currentOrg = persistedOrg || defaultOrg;

        setActiveOrgId(currentOrg);
        await fetchStores(data.session.access_token);
        fetchRoles(data.session.user.id, currentOrg, data.session.access_token);
      }

      setLoading(false);
    };

    init();

    const { data: listener } = supabase.auth.onAuthStateChange((_event, newSession) => {
      setSession(newSession);
      setUser(newSession?.user ?? null);
      if (newSession?.user) {
        const persistedOrg = localStorage.getItem("active_org_id");
        const defaultOrg = newSession.user.user_metadata?.org_id || newSession.user.id;
        const currentOrg = persistedOrg || defaultOrg;

        if (!activeOrgId) setActiveOrgId(currentOrg);

        fetchStores(newSession.access_token);
        fetchRoles(newSession.user.id, currentOrg, newSession.access_token);
      } else {
        setRoles([]);
        setStores([]);
        setActiveOrgId(null);
      }
      setLoading(false);
    });

    return () => {
      listener?.subscription.unsubscribe();
    };
  }, []);

  const switchStore = (newOrgId: string) => {
    setActiveOrgId(newOrgId);
    localStorage.setItem("active_org_id", newOrgId);
    if (user && session) {
      fetchRoles(user.id, newOrgId, session.access_token);
    }
    // Force reload to clear any stale query cache
    window.location.reload();
  };

  const isAdmin = roles.includes("admin");

  const getToken = useCallback(async () => {
    if (disableAuth) return null;
    const { data } = await supabase.auth.getSession();
    return data.session?.access_token ?? null;
  }, [disableAuth]);

  const signOut = useCallback(async () => {
    console.log("[AuthDebug] Initiating Sign Out (disableAuth:", disableAuth, ")");
    setLoading(true);

    try {
      if (!disableAuth) {
        const { error } = await supabase.auth.signOut({ scope: "global" });
        if (error) console.error("Supabase signOut error:", error);
      }
    } catch (e) {
      console.error("Error signing out:", e);
    }

    Object.keys(localStorage).forEach((key) => {
      if (key.startsWith("sb-") || key.includes("supabase") || key === "active_org_id") {
        localStorage.removeItem(key);
      }
    });
    sessionStorage.clear();

    setSession(null);
    setUser(null);
    setRoles([]);
    setStores([]);
    setActiveOrgId(null);
    setLoading(false);

    window.location.href = "/";
  }, [disableAuth]);

  return (
    <AuthContext.Provider value={{ session, user, orgId: activeOrgId, stores, roles, isAdmin, loading, getToken, signOut, switchStore, disableAuth }}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within an AuthProvider");
  return ctx;
};
