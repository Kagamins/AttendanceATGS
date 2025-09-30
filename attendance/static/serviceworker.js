// Define a cache name
const CACHE_NAME = 'version-1';
// List the files to cache
const urlsToCache = [
  '/',
  '/static/css/styles.css', // Add your main CSS file
  '/static/js/main.js'      // Add your main JS file
];

// Install the service worker and cache the files
self.addEventListener('install', function(event) {
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then(function(cache) {
        console.log('Opened cache');
        return cache.addAll(urlsToCache);
      })
  );
});

// Fetch cached files when offline
self.addEventListener('fetch', function(event) {
  event.respondWith(
    caches.match(event.request)
      .then(function(response) {
        // Cache hit - return response
        if (response) {
          return response;
        }
        return fetch(event.request);
      }
    )
  );
});