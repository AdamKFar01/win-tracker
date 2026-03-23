const CACHE_NAME = 'winnerstrackv1';
const STATIC_ASSETS = [
    '/',
    '/static/css/style.css',
    '/static/js/app.js',
    '/static/manifest.json',
    '/static/icons/icon.svg',
    'https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js'
];

self.addEventListener('install', e => {
    e.waitUntil(
        caches.open(CACHE_NAME).then(cache => cache.addAll(STATIC_ASSETS))
    );
    self.skipWaiting();
});

self.addEventListener('activate', e => {
    e.waitUntil(
        caches.keys().then(keys =>
            Promise.all(keys.filter(k => k !== CACHE_NAME).map(k => caches.delete(k)))
        )
    );
    self.clients.claim();
});

self.addEventListener('fetch', e => {
    // API calls always go to network — never cache live data
    if (e.request.url.includes('/api/')) {
        e.respondWith(fetch(e.request));
        return;
    }
    // App shell: cache first, fall back to network
    e.respondWith(
        caches.match(e.request).then(cached => cached || fetch(e.request))
    );
});
