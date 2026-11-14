// 離線閱讀：網路優先，沒網路時才用手機裡存的版本
var CACHE = 'agama-guide-v1';
self.addEventListener('install', function (e) { self.skipWaiting(); });
self.addEventListener('activate', function (e) { e.waitUntil(self.clients.claim()); });
self.addEventListener('fetch', function (e) {
  var req = e.request;
  if (req.method !== 'GET') return;
  var url = new URL(req.url);
  if (url.origin !== location.origin) return;
  if (url.pathname.endsWith('/version.json')) return; // 版本檢查一律走網路
  e.respondWith(
    fetch(req).then(function (res) {
      if (res && res.ok) {
        var copy = res.clone();
        caches.open(CACHE).then(function (c) {
          // 同一個檔案只留最新版本
          c.keys().then(function (ks) { ks.forEach(function (k) { var u = new URL(k.url); if (u.pathname === url.pathname && u.search !== url.search) c.delete(k); }); });
          c.put(req, copy);
        });
      }
      return res;
    }).catch(function () {
      return caches.open(CACHE).then(function (c) {
        return c.match(req).then(function (hit) { return hit || c.match(req, { ignoreSearch: true }); });
      });
    })
  );
});
