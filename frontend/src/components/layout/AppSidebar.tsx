import { Home, Upload, FileText, Settings, LogOut, Building2, BarChart3 } from "lucide-react";
import { NavLink, useNavigate } from "react-router-dom";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { useAuth } from "@/context/AuthContext";

export function AppSidebar() {
    const { signOut } = useAuth();
    const navigate = useNavigate();

    const navItems = [
        { icon: Home, label: "Dashboard", href: "/dashboard" },
        { icon: Upload, label: "Upload", href: "/upload" },
        { icon: BarChart3, label: "Reconciliation", href: "/reconcile" },
        { icon: FileText, label: "AP Sage View", href: "/ap-view" },
        { icon: Building2, label: "Vendors", href: "/vendors" },
        { icon: Settings, label: "Settings", href: "/settings" },
    ];

    const handleLogout = async () => {
        await signOut();
    };

    return (
        <aside className="w-64 border-r bg-card hidden md:flex flex-col h-screen sticky top-0">
            <div className="p-6 border-b flex flex-col gap-4">
                <div className="flex items-center gap-2 px-2">
                    <img src="/logo.png" alt="Cascadia Invoice Assistant" className="h-8 w-auto rounded-lg" />
                    <h2 className="text-lg font-bold text-foreground leading-tight">
                        Cascadia Invoice Assistant
                    </h2>
                </div>
            </div>

            <nav className="flex-1 p-4 space-y-2">
                {navItems.map((item) => (
                    <NavLink
                        key={item.href}
                        to={item.href}
                        className={({ isActive }) =>
                            cn(
                                "flex items-center gap-3 px-4 py-3 rounded-lg transition-colors text-sm font-medium",
                                isActive
                                    ? "bg-primary/10 text-primary"
                                    : "text-muted-foreground hover:bg-muted hover:text-foreground"
                            )
                        }
                    >
                        <item.icon className="h-5 w-5" />
                        {item.label}
                    </NavLink>
                ))}
            </nav>

            <div className="p-4 border-t">
                <Button
                    variant="ghost"
                    className="w-full justify-start gap-3 text-muted-foreground hover:text-destructive"
                    onClick={handleLogout}
                >
                    <LogOut className="h-5 w-5" />
                    Sign Out
                </Button>
            </div>
        </aside>
    );
}
