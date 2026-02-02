import { Home, Upload, Settings, AlertCircle, TrendingUp, FileText } from "lucide-react";
import { NavLink, useNavigate } from "react-router-dom";
import { cn } from "@/lib/utils";
import { useAuth } from "@/context/AuthContext";
import { Button } from "@/components/ui/button";

export function AppHeader() {
    const { user, signOut, isAdmin } = useAuth();
    const navItems = [
        { icon: Home, label: "Dashboard", href: "/dashboard" },
        { icon: AlertCircle, label: "Issue Tracker", href: "/issues" },
        { icon: TrendingUp, label: "AP View", href: "/ap-pos-view" },
        { icon: FileText, label: "Reports", href: "/reports" },
        { icon: Upload, label: "Upload", href: "/upload" },
        // Only show Settings to Admins
        ...(isAdmin ? [{ icon: Settings, label: "Settings", href: "/settings" }] : []),
    ];
    const navigate = useNavigate();

    const handleLogout = async () => {
        await signOut();
    };

    return (
        <header className="border-b bg-card sticky top-0 z-10">
            <div className="container mx-auto px-4 h-16 flex items-center justify-between max-w-7xl">
                <div className="flex items-center gap-8">
                    <div className="flex items-center gap-2">
                        <img src="/logo.png" alt="Cascadia Invoice Assistant" className="h-8 w-auto rounded-lg" />
                        <h2 className="text-xl font-bold text-foreground">
                            Cascadia Invoice Assistant
                        </h2>
                    </div>

                    <nav className="hidden md:flex items-center gap-1">
                        {navItems.map((item) => (
                            <NavLink
                                key={item.href}
                                to={item.href}
                                className={({ isActive }) =>
                                    cn(
                                        "flex items-center gap-2 px-3 py-2 rounded-md transition-colors text-sm font-medium",
                                        isActive
                                            ? "bg-primary/10 text-primary"
                                            : "text-muted-foreground hover:bg-muted hover:text-foreground"
                                    )
                                }
                            >
                                <item.icon className="h-4 w-4" />
                                {item.label}
                            </NavLink>
                        ))}
                    </nav>
                </div>

                <div className="flex items-center gap-4">
                    <span className="text-sm text-muted-foreground hidden sm:inline-block">
                        {user?.email || "Signed in"}
                    </span>
                    <Button variant="outline" size="sm" onClick={handleLogout}>
                        Sign out
                    </Button>
                </div>
            </div>
        </header>
    );
}
