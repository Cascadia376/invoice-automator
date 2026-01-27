export interface UserContext {
    userId: string | null
    email: string | null
    authenticated: boolean
    authRequired: boolean
}

export interface ApiError {
    detail: string
}

export type ApiResponse<T> = {
    data: T | null
    error: string | null
}

export interface HealthResponse {
    status: string
    version: string
    database: string
    auth_required: boolean
    supabase_url: boolean
    supabase_jwt_secret_present: boolean
    jwks_client_ready: boolean
}
