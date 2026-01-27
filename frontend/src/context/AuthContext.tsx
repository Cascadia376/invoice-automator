import React, { createContext, useContext, useEffect, useState, useCallback } from "react";
import { Session, User } from "@supabase/supabase-js";
import { supabase } from "@/lib/supabaseClient";

type AuthContextType = {
  session: Session | null;
  user: User | null;
  orgId: string | null;
  roles: string[];
  loading: boolean;
  getToken: () => Promise<string | null>;
  signOut: () => Promise<void>;
  disableAuth: boolean;
  isAdmin: boolean;
};

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const disableAuth = import.meta.env.VITE_DISABLE_AUTH === "true";
  const [session, setSession] = useState<Session | null>(null);
  const [user, setUser] = useState<User | null>(null);
  const [roles, setRoles] = useState<string[]>([]);
  const [loading, setLoading] = useState(true);

  // Fetch roles from backend
  const fetchRoles = async (userId: string, orgId: string, token: string) => {
    try {
      console.log(`[AuthDebug] Fetching roles for User: ${userId}, Org: ${orgId}`);
      const res = await fetch(`${import.meta.env.VITE_API_URL || 'https://invoice-backend-a1gb.onrender.com'}/api/users/me/roles`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      if (res.ok) {
        const data = await res.json();
        console.log("[AuthDebug] Roles received:", data.roles);
        setRoles(data.roles || []);
      } else {
        console.error("[AuthDebug] Failed to fetch roles:", res.status, await res.text());
      }
    } catch (e) {
      console.error("[AuthDebug] Error fetching roles", e);
    }
  };

  useEffect(() => {
    const init = async () => {
      const { data } = await supabase.auth.getSession();
      setSession(data.session);
      setUser(data.session?.user ?? null);

      if (data.session?.user && data.session?.access_token) {
        const org = data.session.user.user_metadata?.org_id || data.session.user.id;
        fetchRoles(data.session.user.id, org, data.session.access_token);
      }

      setLoading(false);
    };

    init();

    const { data: listener } = supabase.auth.onAuthStateChange((_event, newSession) => {
      setSession(newSession);
      setUser(newSession?.user ?? null);
      if (newSession?.user) {
        const org = newSession.user.user_metadata?.org_id || newSession.user.id;
        fetchRoles(newSession.user.id, org, newSession.access_token);
      } else {
        setRoles([]);
      }
      setLoading(false);
    });

    return () => {
      listener?.subscription.unsubscribe();
    };
  }, []);

  const orgId = user?.user_metadata?.org_id || user?.user_metadata?.organization_id || user?.id || null;
  const isAdmin = roles.includes("admin");

  const getToken = useCallback(async () => {
    if (disableAuth) return null;
    const { data } = await supabase.auth.getSession();
    return data.session?.access_token ?? null;
  }, [disableAuth]);

  const signOut = useCallback(async () => {
    if (disableAuth) return;
    try {
      await supabase.auth.signOut({ scope: "local" });
    } catch (e) {
      console.error("Error signing out:", e);
    }

    // Manually clear Supabase tokens from localStorage to prevent "zombie" sessions
    Object.keys(localStorage).forEach((key) => {
      if (key.startsWith("sb-")) {
        localStorage.removeItem(key);
      }
    });

    // Also clear session storage just in case
    sessionStorage.clear();

    setSession(null);
    setUser(null);
    setRoles([]);
  }, [disableAuth]);

  return (
    <AuthContext.Provider value={{ session, user, orgId, roles, isAdmin, loading, getToken, signOut, disableAuth }}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within an AuthProvider");
  return ctx;
};
