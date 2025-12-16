import { AppHeader } from "./AppHeader";
import { Outlet } from "react-router-dom";

export function DashboardLayout() {
    return (
        <div className="min-h-screen bg-background flex flex-col">
            <AppHeader />
            <main className="flex-1">
                <div className="container mx-auto p-6 md:p-8 max-w-7xl">
                    <Outlet />
                </div>
            </main>
        </div>
    );
}
