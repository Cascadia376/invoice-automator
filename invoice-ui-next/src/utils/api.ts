import { createClient as createServerClient } from '@/utils/supabase/server'
import { createClient as createBrowserClient } from '@/utils/supabase/client'
import { ApiResponse } from '@/types/api'

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

/**
 * A wrapper around fetch that automatically attaches the Supabase access token.
 * Works in both Server Components/Actions and Client Components.
 */
export async function apiFetch<T>(
    endpoint: string,
    options: RequestInit = {}
): Promise<ApiResponse<T>> {
    try {
        const isServer = typeof window === 'undefined'
        const supabase = isServer ? await createServerClient() : createBrowserClient()

        // Get the current session
        const { data: { session } } = await supabase.auth.getSession()
        const token = session?.access_token

        // Prepare headers
        const headers = new Headers(options.headers)
        if (token) {
            headers.set('Authorization', `Bearer ${token}`)
        }
        if (!headers.has('Content-Type') && !(options.body instanceof FormData)) {
            headers.set('Content-Type', 'application/json')
        }

        const url = endpoint.startsWith('http')
            ? endpoint
            : `${API_BASE_URL}${endpoint.startsWith('/') ? '' : '/'}${endpoint}`

        const response = await fetch(url, {
            ...options,
            headers,
        })

        if (!response.ok) {
            const errorData = await response.json().catch(() => ({}))
            return {
                data: null,
                error: errorData.detail || `API Error: ${response.status} ${response.statusText}`
            }
        }

        const data = await response.json()
        return { data, error: null }
    } catch (err: any) {
        console.error('API Fetch failed:', err)
        return {
            data: null,
            error: err.message || 'An unexpected error occurred'
        }
    }
}
