import { Button } from "@/components/ui/button";
import { FileText, Menu, X, LogOut } from "lucide-react";
import { useState } from "react";
import { Link } from "react-router-dom";
import { useAuth } from "@/context/AuthContext";
import { supabase } from "@/lib/supabaseClient";

export const Header = () => {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const { session, user, signOut } = useAuth();

  const handleSignIn = async () => {
    const email = window.prompt("Enter your email to sign in with Supabase");
    if (!email) return;
    await supabase.auth.signInWithOtp({
      email,
      options: {
        emailRedirectTo: window.location.origin,
      },
    });
    alert("Check your email for the magic link to sign in.");
  };

  return (
    <header className="sticky top-0 z-50 w-full border-b border-border/40 bg-background/80 backdrop-blur-xl">
      <nav className="container flex h-16 items-center justify-between">
        <Link to="/" className="flex items-center gap-2 font-semibold text-lg">
          <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-gradient-primary">
            <FileText className="h-5 w-5 text-white" />
          </div>
          <span className="hidden sm:inline-block">InvoiceAI</span>
        </Link>

        {/* Desktop Navigation */}
        <div className="hidden md:flex items-center gap-8">
          <a href="#features" className="text-sm font-medium text-muted-foreground hover:text-foreground transition-colors">
            Features
          </a>
          <a href="#pricing" className="text-sm font-medium text-muted-foreground hover:text-foreground transition-colors">
            Pricing
          </a>
          <a href="#faq" className="text-sm font-medium text-muted-foreground hover:text-foreground transition-colors">
            FAQ
          </a>
        </div>

        <div className="flex items-center gap-3">
          {session ? (
            <>
              <Link to="/dashboard">
                <Button variant="ghost" size="sm" className="hidden md:inline-flex">
                  Dashboard
                </Button>
              </Link>
              <div className="flex items-center gap-2">
                <span className="text-sm text-muted-foreground hidden sm:inline-block">
                  {user?.email || "Signed in"}
                </span>
                <Button variant="ghost" size="icon" onClick={signOut} aria-label="Sign out">
                  <LogOut className="h-4 w-4" />
                </Button>
              </div>
            </>
          ) : (
            <>
              <Button variant="ghost" size="sm" className="hidden md:inline-flex" onClick={handleSignIn}>
                Sign In
              </Button>
              <Button size="sm" className="hidden md:inline-flex" onClick={handleSignIn}>
                Get Started
              </Button>
            </>
          )}

          {/* Mobile Menu Toggle */}
          <Button
            variant="ghost"
            size="icon"
            className="md:hidden"
            onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
          >
            {mobileMenuOpen ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
          </Button>
        </div>
      </nav>

      {/* Mobile Menu */}
      {mobileMenuOpen && (
        <div className="md:hidden border-t border-border/40 bg-background/95 backdrop-blur-xl animate-fade-in">
          <div className="container py-4 space-y-3">
            <a
              href="#features"
              className="block py-2 text-sm font-medium text-muted-foreground hover:text-foreground transition-colors"
              onClick={() => setMobileMenuOpen(false)}
            >
              Features
            </a>
            <a
              href="#pricing"
              className="block py-2 text-sm font-medium text-muted-foreground hover:text-foreground transition-colors"
              onClick={() => setMobileMenuOpen(false)}
            >
              Pricing
            </a>
            <a
              href="#faq"
              className="block py-2 text-sm font-medium text-muted-foreground hover:text-foreground transition-colors"
              onClick={() => setMobileMenuOpen(false)}
            >
              FAQ
            </a>
            <div className="pt-3 space-y-2">
              {session ? (
                <Button variant="ghost" className="w-full" onClick={signOut}>
                  Sign Out
                </Button>
              ) : (
                <>
                  <Button variant="ghost" className="w-full" onClick={handleSignIn}>
                    Sign In
                  </Button>
                  <Button className="w-full" onClick={handleSignIn}>Get Started</Button>
                </>
              )}
            </div>
          </div>
        </div>
      )}
    </header>
  );
};
