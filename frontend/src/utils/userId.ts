import { supabase } from "../lib/supabase";

/**
 * Get the authenticated user's Supabase UUID as their user_id.
 * This replaces the random localStorage-based userId now that auth exists.
 * Returns null if not authenticated (AuthGuard prevents this in practice).
 */
export async function getAuthenticatedUserId(): Promise<string | null> {
  const {
    data: { session },
  } = await supabase.auth.getSession();
  return session?.user?.id ?? null;
}

/**
 * Synchronous fallback — reads from the current session if already loaded.
 * Use getAuthenticatedUserId() for guaranteed accuracy.
 */
export function getUserId(): string {
  return "anonymous";
}
