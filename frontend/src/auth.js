export function getToken() {
  try { return localStorage.getItem('auth_token') || ''; } catch { return ''; }
}

export function setToken(token) {
  try {
    if (token) localStorage.setItem('auth_token', token);
    else localStorage.removeItem('auth_token');
  } catch {}
}

export async function authFetch(url, options = {}) {
  const token = getToken();
  const headers = new Headers(options.headers || {});
  if (token) headers.set('Authorization', `Bearer ${token}`);
  return fetch(url, { ...options, headers });
}
