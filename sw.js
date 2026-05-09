// Service Worker — cache les vidéos en local sur la tablette
// Bump du cache pour invalider l'ancienne version (anciennes vidéos HEVC)
const CACHE_NAME = 'traviata-v2';
const CRITICAL_FILES = [
  './',
  './index.html'
];
const VIDEO_FILES = [
  './01_Acte1_Fete_Brindisi_Valzer.mp4',
  './02_Acte1_Stretta_finale.mp4',
  './03_Acte2_Fete_Flora.mp4'
];

self.addEventListener('install', e => {
  self.skipWaiting();
  e.waitUntil(
    caches.open(CACHE_NAME).then(cache => cache.addAll(CRITICAL_FILES))
  );
});

self.addEventListener('activate', e => {
  e.waitUntil(
    Promise.all([
      self.clients.claim(),
      caches.keys().then(keys => Promise.all(
        keys.filter(k => k !== CACHE_NAME).map(k => caches.delete(k))
      ))
    ])
  );
});

self.addEventListener('fetch', e => {
  const url = new URL(e.request.url);

  // Ignorer tout ce qui n'est pas HTTP/HTTPS (chrome-extension, blob, data, etc.)
  // Ces requêtes ne sont pas cachables et provoquent des erreurs si on essaie.
  if (url.protocol !== 'http:' && url.protocol !== 'https:') return;

  // Ignorer les requêtes Range (vidéos en streaming partiel) : on ne peut pas
  // les cacher proprement, le navigateur s'en occupe mieux directement.
  if (e.request.headers.get('range')) return;

  // Ne cacher que les requêtes du même domaine
  if (url.origin !== self.location.origin) return;

  // Stratégie : cache-first pour les vidéos, network-first pour le reste
  if (url.pathname.endsWith('.mp4')) {
    e.respondWith(
      caches.match(e.request).then(cached => {
        if (cached) return cached;
        return fetch(e.request).then(res => {
          if (res.ok && res.status === 200 && res.type === 'basic') {
            const clone = res.clone();
            caches.open(CACHE_NAME).then(cache =>
              cache.put(e.request, clone).catch(err => console.warn('SW cache put failed:', err))
            );
          }
          return res;
        });
      })
    );
  } else {
    e.respondWith(
      fetch(e.request).then(res => {
        if (res.ok && e.request.method === 'GET' && res.type === 'basic') {
          const clone = res.clone();
          caches.open(CACHE_NAME).then(cache =>
            cache.put(e.request, clone).catch(err => console.warn('SW cache put failed:', err))
          );
        }
        return res;
      }).catch(() => caches.match(e.request))
    );
  }
});

// Message pour précharger les vidéos en arrière-plan
self.addEventListener('message', e => {
  if (e.data && e.data.action === 'precache-videos') {
    caches.open(CACHE_NAME).then(async cache => {
      for (const url of VIDEO_FILES) {
        const existing = await cache.match(url);
        if (!existing) {
          try {
            const res = await fetch(url);
            if (res.ok) await cache.put(url, res);
            self.clients.matchAll().then(clients =>
              clients.forEach(c => c.postMessage({ type: 'video-cached', url }))
            );
          } catch (err) {
            console.warn('Precache failed for', url, err);
          }
        } else {
          self.clients.matchAll().then(clients =>
            clients.forEach(c => c.postMessage({ type: 'video-cached', url }))
          );
        }
      }
      self.clients.matchAll().then(clients =>
        clients.forEach(c => c.postMessage({ type: 'all-cached' }))
      );
    });
  }
});
