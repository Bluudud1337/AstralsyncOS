self.addEventListener("install", () => {
  self.skipWaiting();
});

self.addEventListener("fetch", e => {
  e.respondWith(fetch(e.request));
});
