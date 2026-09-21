// Self-destructing Service Worker to bust old client caches
self.addEventListener('install', (e) => {
  self.skipWaiting();
});

self.addEventListener('activate', (e) => {
  e.waitUntil(
    caches.keys().then((keys) => Promise.all(keys.map((k) => caches.delete(k))))
  );
  self.registration.unregister();
  self.clients.claim();
});

self.addEventListener('fetch', (event) => {
  // Always bypass cache and fetch directly from network
  event.respondWith(fetch(event.request));
});
