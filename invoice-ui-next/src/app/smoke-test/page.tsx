import { apiFetch } from '@/utils/api'
import { HealthResponse, UserContext } from '@/types/api'
import Link from 'next/link'
import { ArrowLeft, Activity, Shield, AlertCircle, CheckCircle2 } from 'lucide-react'

export default async function SmokeTestPage() {
    // Fetch both endpoints in parallel
    const [healthRes, whoAmIRes] = await Promise.all([
        apiFetch<HealthResponse>('/'),
        apiFetch<UserContext>('/api/auth/whoami')
    ])

    return (
        <div className="min-h-screen bg-zinc-950 text-zinc-50 p-8">
            <div className="max-w-3xl mx-auto space-y-8">
                <header className="flex items-center justify-between">
                    <div className="space-y-1">
                        <Link
                            href="/"
                            className="inline-flex items-center gap-2 text-zinc-400 hover:text-white transition-colors text-sm mb-4"
                        >
                            <ArrowLeft size={16} />
                            Back to Dashboard
                        </Link>
                        <h1 className="text-3xl font-bold tracking-tight">Backend Smoke Test</h1>
                        <p className="text-zinc-400">Verify connectivity and authentication sync with FastAPI</p>
                    </div>
                    <Activity className="text-indigo-500 h-12 w-12" />
                </header>

                <div className="grid gap-6">
                    {/* Health Check Section */}
                    <Section
                        title="System Health (/)"
                        icon={<Activity size={20} />}
                        data={healthRes.data}
                        error={healthRes.error}
                    >
                        {healthRes.data && (
                            <div className="grid grid-cols-2 gap-4 mt-4">
                                <StatusItem label="Status" value={healthRes.data.status} />
                                <StatusItem label="Version" value={healthRes.data.version} />
                                <StatusItem label="Database" value={healthRes.data.database} />
                                <StatusItem label="Auth Mode" value={healthRes.data.auth_required ? 'Strict' : 'Log-only'} />
                                <StatusBool label="Supabase URL" value={healthRes.data.supabase_url} />
                                <StatusBool label="JWKS Ready" value={healthRes.data.jwks_client_ready} />
                            </div>
                        )}
                    </Section>

                    {/* WhoAmI Section */}
                    <Section
                        title="Authentication Context (/api/auth/whoami)"
                        icon={<Shield size={20} />}
                        data={whoAmIRes.data}
                        error={whoAmIRes.error}
                    >
                        {whoAmIRes.data && (
                            <div className="mt-4 space-y-4">
                                <div className="p-4 rounded-xl bg-zinc-800/50 border border-zinc-700">
                                    <div className="text-xs text-zinc-500 uppercase font-bold tracking-wider mb-2">Decoded Identity</div>
                                    <div className="space-y-2">
                                        <div className="flex justify-between items-center">
                                            <span className="text-zinc-400 text-sm">User ID:</span>
                                            <code className="text-xs bg-zinc-900 px-2 py-1 rounded text-indigo-400">
                                                {whoAmIRes.data.userId || 'null'}
                                            </code>
                                        </div>
                                        <div className="flex justify-between items-center">
                                            <span className="text-zinc-400 text-sm">Email:</span>
                                            <span className="text-sm font-medium">{whoAmIRes.data.email || 'None'}</span>
                                        </div>
                                    </div>
                                </div>
                                <div className="grid grid-cols-2 gap-4">
                                    <StatusBool label="Authenticated" value={whoAmIRes.data.authenticated} />
                                    <StatusBool label="Auth Required" value={whoAmIRes.data.authRequired} />
                                </div>
                            </div>
                        )}
                    </Section>
                </div>

                <footer className="text-center pt-8 border-t border-zinc-800">
                    <p className="text-sm text-zinc-500 italic">
                        Note: If authentication fails, ensure your NEXT_PUBLIC_SUPABASE_URL
                        matches the backend's SUPABASE_URL exactly.
                    </p>
                </footer>
            </div>
        </div>
    )
}

function Section({ title, icon, data, error, children }: {
    title: string;
    icon: React.ReactNode;
    data: any;
    error: string | null;
    children: React.ReactNode;
}) {
    return (
        <div className="bg-zinc-900 border border-zinc-800 rounded-2xl p-6 shadow-sm overflow-hidden">
            <div className="flex items-center justify-between mb-4">
                <div className="flex items-center gap-3">
                    <div className="p-2 bg-indigo-500/10 text-indigo-500 rounded-lg">
                        {icon}
                    </div>
                    <h2 className="font-semibold text-white">{title}</h2>
                </div>
                {error ? (
                    <span className="flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-red-500/10 text-red-500 border border-red-500/20 text-xs font-bold">
                        <AlertCircle size={12} />
                        Failed
                    </span>
                ) : data ? (
                    <span className="flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-green-500/10 text-green-500 border border-green-500/20 text-xs font-bold">
                        <CheckCircle2 size={12} />
                        Success
                    </span>
                ) : null}
            </div>

            {error && (
                <div className="p-4 rounded-xl bg-red-500/5 border border-red-500/20 text-red-400 text-sm font-medium">
                    {error}
                </div>
            )}

            {children}
        </div>
    )
}

function StatusItem({ label, value }: { label: string; value: string }) {
    return (
        <div className="flex flex-col gap-1 p-3 rounded-xl bg-zinc-800/30 border border-zinc-700/50">
            <span className="text-[10px] text-zinc-500 uppercase font-bold tracking-wider">{label}</span>
            <span className="text-sm font-medium">{value}</span>
        </div>
    )
}

function StatusBool({ label, value }: { label: string; value: boolean }) {
    return (
        <div className="flex items-center justify-between p-3 rounded-xl bg-zinc-800/30 border border-zinc-700/50">
            <span className="text-xs text-zinc-400">{label}</span>
            {value ? (
                <CheckCircle2 size={16} className="text-green-500" />
            ) : (
                <AlertCircle size={16} className="text-zinc-600" />
            )}
        </div>
    )
}
