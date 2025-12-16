import { Home, Upload, FileText, Settings } from "lucide-react";
import { NavLink } from "react-router-dom";
import { cn } from "@/lib/utils";
import { UserButton, OrganizationSwitcher } from "@clerk/clerk-react";

export function AppHeader() {
    const navItems = [
        { icon: Home, label: "Dashboard", href: "/dashboard" },
        { icon: Upload, label: "Upload", href: "/upload" },
        { icon: Settings, label: "Settings", href: "/settings" },
    ];

    return (
        <header className="border-b bg-card sticky top-0 z-10">
            <div className="container mx-auto px-4 h-16 flex items-center justify-between max-w-7xl">
                <div className="flex items-center gap-8">
                    <h2 className="text-xl font-bold bg-gradient-to-r from-primary to-purple-600 bg-clip-text text-transparent">
                        InvoiceZen
                    </h2>
                    <OrganizationSwitcher
                        afterCreateOrganizationUrl="/dashboard"
                        afterLeaveOrganizationUrl="/dashboard"
                        afterSelectOrganizationUrl="/dashboard"
                        appearance={{
                            elements: {
                                rootBox: "flex items-center",
                                organizationSwitcherTrigger: "flex items-center gap-2 px-3 py-2 rounded-md hover:bg-muted/50 transition-colors"
                            }
                        }}
                    />

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
                    <UserButton afterSignOutUrl="/" />
                </div>
            </div>
        </header>
    );
}
