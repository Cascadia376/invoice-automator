import React, { useEffect, useState } from "react";
import { useAuth } from "@/context/AuthContext";
import { ArrowLeft, Activity, Shield, AlertCircle, CheckCircle2 } from "lucide-react";
import { Link } from "react-router-dom";

interface HealthRes {
    status: string;
    version: string;
    database: string;
    auth_required: boolean;
}

interface WhoAmIRes {
    user_id: string | null;
    email: string | null;
    authenticated: boolean;
    auth_required: boolean;
}

const SmokeTest = () => {
    const { getToken } = useAuth();
    const [health, setHealth] = useState<{ data: HealthRes | null; error: string | null }>({ data: null, error: null });
    const [whoami, setWhoami] = useState<{ data: WhoAmIRes | null; error: string | null }>({ data: null, error: null });
    const [loading, setLoading] = useState(true);

    const API_URL = import.meta.env.VITE_API_URL || 'https://invoice-backend-a1gb.onrender.com';

    useEffect(() => {
        const fetchData = async () => {
            setLoading(true);
            const token = await getToken();

            // Health Check
            try {
                const hRes = await fetch(`${API_URL}/health`);
                if (hRes.ok) setHealth({ data: await hRes.json(), error: null });
                else setHealth({ data: null, error: `Error ${hRes.status}` });
            } catch (e: any) {
                setHealth({ data: null, error: e.message });
            }

            // WhoAmI
            try {
                const wRes = await fetch(`${API_URL}/whoami`, {
                    headers: token ? { Authorization: `Bearer ${token}` } : {}
                });
                if (wRes.ok) setWhoami({ data: await wRes.json(), error: null });
                else setWhoami({ data: null, error: `Error ${wRes.status}` });
            } catch (e: any) {
                setWhoami({ data: null, error: e.message });
            }

            setLoading(false);
        };

        fetchData();
    }, [getToken, API_URL]);

    return (
        <div className="min-h-screen bg-gray-50 p-8 font-sans">
            <div className="max-w-3xl mx-auto space-y-8">
                <header className="flex items-center justify-between">
                    <div className="space-y-1">
                        <Link
                            to="/"
                            className="inline-flex items-center gap-2 text-gray-500 hover:text-gray-800 transition-colors text-sm mb-4"
                        >
                            <ArrowLeft size={16} />
                            Back to Dashboard
                        </Link>
                        <h1 className="text-3xl font-bold text-gray-900">Backend Smoke Test</h1>
                        <p className="text-gray-600">Checking connection to {API_URL}</p>
                    </div>
                    <Activity className="text-blue-600 h-12 w-12" />
                </header>

                {loading ? (
                    <div className="text-center py-20 bg-white rounded-2xl border border-gray-200">
                        <p className="text-gray-500 animate-pulse font-medium">Running diagnostics...</p>
                    </div>
                ) : (
                    <div className="grid gap-6">
                        <Section title="System Health (/health)" data={health.data} error={health.error}>
                            {health.data && (
                                <div className="grid grid-cols-2 gap-4 mt-2">
                                    <div className="bg-gray-100 p-3 rounded-lg"><span className="text-xs text-gray-500 block">Status</span>{health.data.status}</div>
                                    <div className="bg-gray-100 p-3 rounded-lg"><span className="text-xs text-gray-500 block">Version</span>{health.data.version}</div>
                                    <div className="bg-gray-100 p-3 rounded-lg"><span className="text-xs text-gray-500 block">DB</span>{health.data.database}</div>
                                    <div className="bg-gray-100 p-3 rounded-lg"><span className="text-xs text-gray-500 block">Enforcement</span>{health.data.auth_required ? 'Strict' : 'Log-only'}</div>
                                </div>
                            )}
                        </Section>

                        <Section title="Auth Context (/whoami)" data={whoami.data} error={whoami.error}>
                            {whoami.data && (
                                <div className="mt-2 space-y-4">
                                    <div className="bg-gray-100 p-4 rounded-lg font-mono text-xs break-all">
                                        <span className="text-gray-500 block mb-1">Decoded userId</span>
                                        {whoami.data.user_id || 'null'}
                                    </div>
                                    <div className="flex gap-4">
                                        <div className={`p-3 rounded-lg flex-1 border ${whoami.data.authenticated ? 'bg-green-50 border-green-200 text-green-700' : 'bg-gray-100 border-gray-200 text-gray-500'}`}>
                                            <span className="text-[10px] block uppercase font-bold mb-1">Authenticated</span>
                                            {whoami.data.authenticated ? 'YES' : 'NO'}
                                        </div>
                                        <div className="bg-gray-100 p-3 rounded-lg flex-1 border border-gray-200">
                                            <span className="text-[10px] block uppercase font-bold mb-1 text-gray-500">Backend Required</span>
                                            {whoami.data.auth_required ? 'YES' : 'NO'}
                                        </div>
                                    </div>
                                </div>
                            )}
                        </Section>
                    </div>
                )}
            </div>
        </div>
    );
};

const Section = ({ title, data, error, children }: any) => (
    <div className="bg-white border border-gray-200 rounded-2xl p-6 shadow-sm shadow-gray-100/50">
        <div className="flex items-center justify-between mb-4">
            <h2 className="font-bold text-gray-800">{title}</h2>
            {error ? (
                <AlertCircle className="text-red-500" size={20} />
            ) : data ? (
                <CheckCircle2 className="text-green-500" size={20} />
            ) : null}
        </div>
        {error && <div className="text-red-500 text-sm bg-red-50 p-3 rounded-lg border border-red-100 mb-2">{error}</div>}
        {children}
    </div>
);

export default SmokeTest;
