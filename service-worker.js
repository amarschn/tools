// Transparent Tools – Service Worker
// Cache-first for local assets and pinned calculation runtimes; other CDN
// resources are network-first.
// Designed to be lightweight and safe: failures fall through to the network.

const CACHE_VERSION = 'tt-cache-v3';
const MAX_CACHE_ENTRIES = 100;
const NETWORK_FALLBACK_DELAY_MS = 1000;
const NAVIGATION_FALLBACK_DELAY_MS = 750;
const HOMEPAGE_DATA_FALLBACK_DELAY_MS = 250;

// Assets to pre-cache on install.
const PRECACHE_URLS = [
  './',
  './about.html',
  './catalog.json',
  './data/homepage-tool-meta.json',
  './shared/homepage-index.js'
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
            .filter(
              (key) => key.startsWith('tt-cache-') && key !== CACHE_VERSION
            )
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

function isVersionedCalculationAsset(url) {
  const parsed = new URL(url);
  // Exact Pyodide releases are immutable. Revalidating the loader, WASM and
  // stdlib in successive startup phases makes a weak connection feel frozen.
  if (parsed.origin === 'https://cdn.jsdelivr.net' &&
      /^\/pyodide\/v\d+\.\d+\.\d+\/full\//.test(parsed.pathname)) return true;
  // These Python modules share the thread page's content-derived asset key.
  // Unversioned sources must keep revalidating so development edits stay fresh.
  return parsed.origin === self.location.origin &&
    /\/pycalcs\/(fasteners|threads|thread_specifications|thread_models)\.py$/.test(parsed.pathname) &&
    /^thread-[a-f0-9]{16}$/.test(parsed.searchParams.get('v') || '');
}

function isStaticAsset(url) {
  return /\.(html|css|js|json|png|jpg|svg|woff2?|ico)(\?.*)?$/.test(url);
}

function isHomepageData(url) {
  const pathname = new URL(url).pathname;
  return pathname.endsWith('/catalog.json') ||
    pathname.endsWith('/data/homepage-tool-meta.json') ||
    pathname.endsWith('/shared/homepage-index.js');
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
async function cacheFirstOutcome(request) {
  const cache = await caches.open(CACHE_VERSION);
  const cached = await cache.match(request);
  if (cached) return { response: cached, shouldCache: false };

  const response = await fetch(request);
  return { response, shouldCache: true };
}

/**
 * Store a response without delaying delivery to the page.
 */
async function storeResponse(request, response) {
  if (!response.ok) return;
  const copy = response.clone();
  const cache = await caches.open(CACHE_VERSION);
  await cache.put(request, copy);
  await trimCache(CACHE_VERSION, MAX_CACHE_ENTRIES);
}

/**
 * Prefer a fresh response, but stop making returning visitors wait after a
 * short delay when a cached response is available. The network request keeps
 * running so the next navigation receives the newest response.
 */
async function boundedNetworkFirst(request, networkPromise, delayMs) {
  const cache = await caches.open(CACHE_VERSION);
  const cached = await cache.match(request);
  if (!cached) return networkPromise;

  let timerId;
  const cachedFallback = new Promise((resolve) => {
    timerId = setTimeout(() => resolve(cached), delayMs);
  });
  const preferredNetwork = networkPromise
    .then((response) => response.ok ? response : cached)
    .catch(() => cached);

  try {
    return await Promise.race([preferredNetwork, cachedFallback]);
  } finally {
    clearTimeout(timerId);
  }
}

function respondNetworkFirst(event, delayMs = NETWORK_FALLBACK_DELAY_MS) {
  const networkPromise = fetch(event.request);
  const cacheUpdate = networkPromise
    .then((response) => storeResponse(event.request, response))
    .catch(() => undefined);
  event.waitUntil(cacheUpdate);
  event.respondWith(
    boundedNetworkFirst(event.request, networkPromise, delayMs)
  );
}

function respondCacheFirst(event) {
  const outcomePromise = cacheFirstOutcome(event.request);
  const cacheUpdate = outcomePromise
    .then((outcome) => outcome.shouldCache
      ? storeResponse(event.request, outcome.response)
      : undefined)
    .catch(() => undefined);
  const responsePromise = outcomePromise.then((outcome) => outcome.response);
  event.waitUntil(cacheUpdate);
  event.respondWith(responsePromise);
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

  if (isVersionedCalculationAsset(url)) {
    respondCacheFirst(event);
    return;
  }

  // CDN resources: network-first so we pick up updates, but still usable offline
  if (isCdnRequest(url)) {
    respondNetworkFirst(event);
    return;
  }

  // Prefer fresh navigations, with a bounded wait on weak connections.
  if (request.mode === 'navigate') {
    respondNetworkFirst(event, NAVIGATION_FALLBACK_DELAY_MS);
    return;
  }

  // Cached homepage data should never hold up the interactive index.
  if (isHomepageData(url)) {
    respondNetworkFirst(event, HOMEPAGE_DATA_FALLBACK_DELAY_MS);
    return;
  }

  // Other local static assets remain cache-first for speed and offline use.
  if (isStaticAsset(url)) {
    respondCacheFirst(event);
    return;
  }

  // Everything else: try network, fall back to cache
  respondNetworkFirst(event);
});
