// REST + SSE client. The bearer token (for phone / Tailscale access) is stored
// in localStorage; loopback dev needs none. SSE passes it as ?token=.

import type { Genome, Pet } from '@yao/core';

const TOKEN_KEY = 'yao_token';

export const getToken = (): string => localStorage.getItem(TOKEN_KEY) ?? '';
export const setToken = (t: string): void => localStorage.setItem(TOKEN_KEY, t);

export class AuthError extends Error {}

export interface PetView {
  pet: Pet;
  genome?: Genome;
  svg: string;
  whispers?: { id: number; text: string; source: string; createdAt: number }[];
}

async function req<T>(path: string, init: RequestInit = {}): Promise<T> {
  const token = getToken();
  const headers = new Headers(init.headers);
  headers.set('content-type', 'application/json');
  if (token) headers.set('authorization', `Bearer ${token}`);
  const res = await fetch(path, { ...init, headers });
  if (res.status === 401) throw new AuthError('unauthorized');
  if (!res.ok) throw new Error(`${res.status} ${await res.text()}`);
  return res.json() as Promise<T>;
}

export const api = {
  health: () => req<{ ok: boolean; llm: { provider: string; available: boolean } }>('/api/health'),
  listPets: () => req<PetView[]>('/api/pets'),
  createPet: (body: { name?: string; seed?: string }) =>
    req<PetView>('/api/pets', { method: 'POST', body: JSON.stringify(body) }),
  getPet: (id: string) => req<PetView>(`/api/pets/${id}`),
  interact: (id: string, action: string, value?: string) =>
    req<PetView>(`/api/pets/${id}/interact`, {
      method: 'POST',
      body: JSON.stringify({ action, value }),
    }),
  streamUrl: (id: string): string => {
    const token = getToken();
    return `/api/stream/${id}${token ? `?token=${encodeURIComponent(token)}` : ''}`;
  },
};
