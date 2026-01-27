import { login, signup } from './actions'

export default function LoginPage({
    searchParams,
}: {
    searchParams: { error?: string }
}) {
    return (
        <div className="flex min-h-screen flex-col items-center justify-center bg-zinc-950 px-4 text-zinc-50">
            <div className="w-full max-w-sm space-y-8 rounded-2xl bg-zinc-900/50 p-8 shadow-2xl backdrop-blur-sm border border-zinc-800">
                <div className="text-center">
                    <h1 className="text-3xl font-bold tracking-tight text-white">
                        Invoice Automator
                    </h1>
                    <p className="mt-2 text-sm text-zinc-400">
                        Sign in to your account to continue
                    </p>
                </div>

                <form className="mt-8 space-y-6">
                    <div className="space-y-4 rounded-md shadow-sm">
                        <div>
                            <label htmlFor="email" className="block text-sm font-medium text-zinc-400 mb-1">
                                Email address
                            </label>
                            <input
                                id="email"
                                name="email"
                                type="email"
                                autoComplete="email"
                                required
                                className="w-full rounded-lg bg-zinc-800 border-zinc-700 px-4 py-2.5 text-white placeholder-zinc-500 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent transition-all"
                                placeholder="name@example.com"
                            />
                        </div>
                        <div>
                            <label htmlFor="password" role="text" className="block text-sm font-medium text-zinc-400 mb-1">
                                Password
                            </label>
                            <input
                                id="password"
                                name="password"
                                type="password"
                                autoComplete="current-password"
                                required
                                className="w-full rounded-lg bg-zinc-800 border-zinc-700 px-4 py-2.5 text-white placeholder-zinc-500 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent transition-all"
                                placeholder="••••••••"
                            />
                        </div>
                    </div>

                    {searchParams?.error && (
                        <div className="p-3 rounded-lg bg-red-500/10 border border-red-500/20 text-red-500 text-sm animate-in fade-in slide-in-from-top-1">
                            {searchParams.error}
                        </div>
                    )}

                    <div className="flex flex-col gap-3">
                        <button
                            formAction={login}
                            className="w-full flex justify-center py-2.5 px-4 rounded-lg bg-indigo-600 font-semibold text-white hover:bg-indigo-500 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-600 transition-all font-medium"
                        >
                            Sign in
                        </button>
                        <button
                            formAction={signup}
                            className="w-full flex justify-center py-2.5 px-4 rounded-lg border border-zinc-700 font-semibold text-zinc-300 hover:bg-zinc-800 focus:outline-none transition-all font-medium"
                        >
                            Request Access (Sign Up)
                        </button>
                    </div>
                </form>
            </div>
        </div>
    )
}
