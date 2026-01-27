import { createClient } from '@/utils/supabase/server'
import { signOut } from './login/actions'
import { LogOut, User, ShieldCheck, ShieldAlert, Activity } from 'lucide-react'
import { apiFetch } from '@/utils/api'
import { UserContext } from '@/types/api'
import Link from 'next/link'

export default async function HomePage() {
  const supabase = await createClient()

  const {
    data: { user },
  } = await supabase.auth.getUser()

  // Example: Calling the backend to verify the token works
  const { data: whoAmI, error: apiError } = await apiFetch<UserContext>('/api/auth/whoami')

  return (
    <div className="flex min-h-screen flex-col bg-zinc-950 text-zinc-50">
      {/* Header */}
      <nav className="border-b border-zinc-800 bg-zinc-900/50 backdrop-blur-md sticky top-0 z-50">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
          <div className="flex h-16 items-center justify-between">
            <div className="flex items-center gap-2">
              <div className="h-8 w-8 rounded-lg bg-indigo-600 flex items-center justify-center">
                <span className="font-bold text-lg">I</span>
              </div>
              <span className="text-xl font-bold text-white tracking-tight">
                Automator
              </span>
            </div>
            <div className="flex items-center gap-4">
              {/* Backend Status Badge */}
              {whoAmI?.authenticated ? (
                <div className="flex items-center gap-1.5 px-3 py-1 rounded-full bg-green-500/10 text-green-500 border border-green-500/20 text-xs font-semibold">
                  <ShieldCheck size={14} />
                  Backend Protected
                </div>
              ) : (
                <div className="flex items-center gap-1.5 px-3 py-1 rounded-full bg-red-500/10 text-red-500 border border-red-500/20 text-xs font-semibold">
                  <ShieldAlert size={14} />
                  Backend Sync Failed
                </div>
              )}

              <div className="flex items-center gap-3 px-3 py-1.5 rounded-full bg-zinc-800 border border-zinc-700">
                <User size={16} className="text-zinc-400" />
                <span className="text-sm font-medium text-zinc-300">
                  {user?.email}
                </span>
              </div>
              <form action={signOut}>
                <button className="flex items-center gap-2 px-4 py-2 rounded-lg bg-zinc-800 hover:bg-zinc-700 text-zinc-300 text-sm font-medium transition-colors border border-zinc-700">
                  <LogOut size={16} />
                  Sign Out
                </button>
              </form>
            </div>
          </div>
        </div>
      </nav>

      {/* Hero Section */}
      <main className="flex-1">
        <div className="mx-auto max-w-7xl px-4 py-12 sm:px-6 lg:px-8">
          <div className="rounded-2xl bg-gradient-to-br from-indigo-900/20 via-zinc-900 to-zinc-900 border border-zinc-800 p-12 text-center">
            <h2 className="text-4xl font-extrabold text-white sm:text-5xl lg:text-6xl tracking-tight">
              Welcome back, <span className="text-indigo-500">Explorer</span>
            </h2>
            <p className="mt-6 text-xl text-zinc-400 max-w-2xl mx-auto">
              You are securely logged in to the Invoice Automator portal. Manage your accounts, monitor your data, and scale your workflow effortlessly.
            </p>
            <div className="mt-10 flex items-center justify-center gap-6">
              <button className="px-8 py-3 rounded-xl bg-indigo-600 text-white font-bold hover:bg-indigo-500 transition-all shadow-lg shadow-indigo-500/10">
                Get Started
              </button>
              <Link
                href="/smoke-test"
                className="flex items-center gap-2 px-8 py-3 rounded-xl bg-zinc-800 text-zinc-300 font-bold hover:bg-zinc-700 transition-all border border-zinc-700"
              >
                <Activity size={18} />
                Smoke Test
              </Link>
            </div>
          </div>

          {/* Quick Stats Grid */}
          <div className="mt-12 grid grid-cols-1 gap-8 sm:grid-cols-2 lg:grid-cols-3">
            <StatCard title="Total Invoices" value="1,284" change="+12.5%" />
            <StatCard title="Processed Today" value="86" change="+5.2%" />
            <StatCard title="Accuracy Rate" value="99.9%" change="Stable" />
          </div>
        </div>
      </main>
    </div>
  )
}

function StatCard({ title, value, change }: { title: string; value: string; change: string }) {
  return (
    <div className="rounded-xl bg-zinc-900 border border-zinc-800 p-6">
      <p className="text-sm font-medium text-zinc-400">{title}</p>
      <div className="mt-2 flex items-baseline justify-between">
        <p className="text-3xl font-bold text-white">{value}</p>
        <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${change.startsWith('+') ? 'bg-green-500/10 text-green-500' : 'bg-zinc-800 text-zinc-400'
          }`}>
          {change}
        </span>
      </div>
    </div>
  )
}
