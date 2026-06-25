// Focus PWA service worker.
// Strategy: precache the app shell so launches are instant and work offline;
// never cache Supabase API traffic (data must stay fresh). Bump CACHE on any
// shell change so clients pick up the new version.
const CACHE = 'focus-shell-v1';
const SHELL = [
  './',
  './index.html',
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
  if (req.method !== 'GET') return;                         // never touch writes
  const url = new URL(req.url);
  // Supabase (auth + data) and any cross-origin API: always go to the network.
  if (url.hostname.endsWith('.supabase.co')) return;

  if (req.mode === 'navigate') {
    // App shell: serve cached index instantly, refresh in the background.
    event.respondWith(caches.match('./index.html').then((cached) => cached || fetch(req)));
    return;
  }
  // Static assets: cache-first, fall back to network and cache the result.
  event.respondWith(
    caches.match(req).then((cached) =>
      cached ||
      fetch(req).then((res) => {
        const copy = res.clone();
        if (res.ok && url.origin === self.location.origin) {
          caches.open(CACHE).then((c) => c.put(req, copy));
        }
        return res;
      })
    )
  );
});
