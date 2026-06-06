"use client";

import { useSyncExternalStore } from "react";
import { useParams } from "next/navigation";

/** localStorage key holding the last-selected username. */
export const CURRENT_USER_KEY = "job-agent:username";

/** Custom event fired on same-tab writes (the `storage` event is cross-tab only). */
const CHANGE_EVENT = "job-agent:user-change";

/** Persist the selected username to localStorage (no-op if unavailable). */
export function setCurrentUser(username: string): void {
  if (typeof window === "undefined") return;
  try {
    window.localStorage.setItem(CURRENT_USER_KEY, username);
    window.dispatchEvent(new Event(CHANGE_EVENT));
  } catch {
    // localStorage unavailable (private mode, blocked) — non-fatal.
  }
}

function readStored(): string | null {
  try {
    return window.localStorage.getItem(CURRENT_USER_KEY);
  } catch {
    return null;
  }
}

/** Read the last-selected username from localStorage, or null. */
export function getStoredUser(): string | null {
  if (typeof window === "undefined") return null;
  return readStored();
}

function subscribe(callback: () => void): () => void {
  window.addEventListener("storage", callback);
  window.addEventListener(CHANGE_EVENT, callback);
  return () => {
    window.removeEventListener("storage", callback);
    window.removeEventListener(CHANGE_EVENT, callback);
  };
}

/**
 * Current-user hook.
 *
 * The active username comes from the `[username]` route segment. On routes
 * without it (e.g. the `/` picker) the value persisted in localStorage is used
 * as a fallback. Subscribing via `useSyncExternalStore` keeps the top-bar
 * selector in sync with the stored choice across tabs and same-tab writes.
 */
export function useCurrentUser(): string | null {
  const params = useParams();
  const routeUser =
    typeof params?.username === "string" ? params.username : null;
  const stored = useSyncExternalStore(subscribe, readStored, () => null);
  return routeUser ?? stored;
}
