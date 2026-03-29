// Transparent Tools – Service Worker
// Cache-first for local assets, network-first for CDN resources.
// Designed to be lightweight and safe: failures fall through to the network.

const CACHE_VERSION = 'tt-cache-v1';
const MAX_CACHE_ENTRIES = 100;

// Assets to pre-cache on install (landing + about pages)
const PRECACHE_URLS = [
  '/',
  '/index.html',
  '/about.html'
];

// Patterns that should NEVER be cached
const NEVER_CACHE = [
  /google-analytics\.com/,
  /googletagmanager\.com/,
  /analytics/,
  /localhost/
];

// CDN origins that use a network-first strategy
const CDN_ORIGINS = [
  'cdn.plot.ly',
  'cdn.jsdelivr.net',
  'cdnjs.cloudflare.com',
  'pyodide-cdn2.iodide.io',
  'cdn.pyodide.org',
  'mathjax.org'
];

// ---------------------------------------------------------------------------
// Install – pre-cache the landing page and about page
// ---------------------------------------------------------------------------
self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_VERSION)
      .then((cache) => cache.addAll(PRECACHE_URLS))
      .then(() => self.skipWaiting())
      .catch((err) => {
        // Pre-caching is best-effort; don't block activation.
        console.warn('[SW] Pre-cache failed:', err);
        return self.skipWaiting();
      })
  );
});

// ---------------------------------------------------------------------------
// Activate – remove old caches
// ---------------------------------------------------------------------------
self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys()
      .then((keys) =>
        Promise.all(
          keys
            .filter((key) => key !== CACHE_VERSION)
            .map((key) => caches.delete(key))
        )
      )
      .then(() => self.clients.claim())
  );
});

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function shouldNeverCache(url) {
  return NEVER_CACHE.some((pattern) => pattern.test(url));
}

function isCdnRequest(url) {
  return CDN_ORIGINS.some((origin) => url.includes(origin));
}

function isStaticAsset(url) {
  return /\.(html|css|js|json|png|jpg|svg|woff2?|ico)(\?.*)?$/.test(url);
}

/**
 * Trim the cache to MAX_CACHE_ENTRIES by removing the oldest entries.
 */
async function trimCache(cacheName, maxEntries) {
  const cache = await caches.open(cacheName);
  const keys = await cache.keys();
  if (keys.length > maxEntries) {
    // Delete oldest entries first (FIFO)
    const toDelete = keys.slice(0, keys.length - maxEntries);
    await Promise.all(toDelete.map((key) => cache.delete(key)));
  }
}

// ---------------------------------------------------------------------------
// Fetch strategies
// ---------------------------------------------------------------------------

/**
 * Cache-first: return cached response if available, else fetch from network
 * and cache the result for future offline use.
 */
async function cacheFirst(request) {
  const cached = await caches.match(request);
  if (cached) return cached;

  const response = await fetch(request);
  if (response.ok) {
    const cache = await caches.open(CACHE_VERSION);
    cache.put(request, response.clone());
    trimCache(CACHE_VERSION, MAX_CACHE_ENTRIES);
  }
  return response;
}

/**
 * Network-first: try the network, fall back to cache.
 * Successful network responses are cached for offline use.
 */
async function networkFirst(request) {
  try {
    const response = await fetch(request);
    if (response.ok) {
      const cache = await caches.open(CACHE_VERSION);
      cache.put(request, response.clone());
      trimCache(CACHE_VERSION, MAX_CACHE_ENTRIES);
    }
    return response;
  } catch (_err) {
    const cached = await caches.match(request);
    if (cached) return cached;
    // Nothing in cache either – let the browser handle the error.
    throw _err;
  }
}

// ---------------------------------------------------------------------------
// Fetch event
// ---------------------------------------------------------------------------
self.addEventListener('fetch', (event) => {
  const { request } = event;
  const url = request.url;

  // Only handle GET requests
  if (request.method !== 'GET') return;

  // Never cache analytics or localhost dev requests
  if (shouldNeverCache(url)) return;

  // CDN resources: network-first so we pick up updates, but still usable offline
  if (isCdnRequest(url)) {
    event.respondWith(networkFirst(request));
    return;
  }

  // Local static assets and tool pages: cache-first for speed and offline use
  if (isStaticAsset(url) || request.mode === 'navigate') {
    event.respondWith(cacheFirst(request));
    return;
  }

  // Everything else: try network, fall back to cache
  event.respondWith(networkFirst(request));
});
