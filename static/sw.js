// Focus PWA service worker.
// Navigations are network-first (so a stale/redirected cache entry can never
// brick the site); only the offline fallback comes from cache. Supabase traffic
// is never touched. Bump CACHE on any shell change to replace older versions.
const CACHE = 'focus-shell-v3';
// NB: precache '/' (the canonical URL) — never '/index.html', which Cloudflare
// Pages 308-redirects to '/'. Caching a redirected response and serving it for a
// navigation triggers a hard ERR_FAILED in Chrome.
const SHELL = [
  './',
  './manifest.json',
  './icons/icon-192.png',
  './icons/icon-512.png',
  './icons/apple-touch-icon.png',
];

self.addEventListener('install', (event) => {
  event.waitUntil(caches.open(CACHE).then((c) => c.addAll(SHELL)).then(() => self.skipWaiting()));
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys()
      .then((keys) => Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k))))
      .then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', (event) => {
  const req = event.request;
  if (req.method !== 'GET') return;                          // never touch writes
  const url = new URL(req.url);
  if (url.hostname.endsWith('.supabase.co')) return;         // data + auth: always live

  // Page loads: hit the network first; fall back to the cached shell only offline.
  if (req.mode === 'navigate') {
    event.respondWith(fetch(req).catch(() => caches.match('./')));
    return;
  }

  // Same-origin static assets: cache-first, then populate the cache.
  if (url.origin === self.location.origin) {
    event.respondWith(
      caches.match(req).then((cached) =>
        cached ||
        fetch(req).then((res) => {
          if (res.ok) { const copy = res.clone(); caches.open(CACHE).then((c) => c.put(req, copy)); }
          return res;
        })
      )
    );
  }
  // Cross-origin (CDN libraries, fonts): leave to the browser — don't intercept.
});
