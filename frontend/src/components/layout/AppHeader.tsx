import { Home, Upload, Settings, AlertCircle } from "lucide-react";
import { NavLink } from "react-router-dom";
import { cn } from "@/lib/utils";
import { useAuth } from "@/context/AuthContext";
import { Button } from "@/components/ui/button";

export function AppHeader() {
    const { user, signOut } = useAuth();
    const navItems = [
        { icon: Home, label: "Dashboard", href: "/dashboard" },
        { icon: AlertCircle, label: "Issue Tracker", href: "/issues" },
        { icon: Upload, label: "Upload", href: "/upload" },
        { icon: Settings, label: "Settings", href: "/settings" },
    ];

    return (
        <header className="border-b bg-card sticky top-0 z-10">
            <div className="container mx-auto px-4 h-16 flex items-center justify-between max-w-7xl">
                <div className="flex items-center gap-8">
                    <h2 className="text-xl font-bold text-foreground">
                        Cascadia Invoice Agent
                    </h2>

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
                    <Button variant="outline" size="sm" onClick={signOut}>
                        Sign out
                    </Button>
                </div>
            </div>
        </header>
    );
}
