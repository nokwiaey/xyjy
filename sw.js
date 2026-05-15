// Service Worker - 离线缓存
const CACHE_NAME = 'xyjy-tools-v1';

// 需要预缓存的静态资源
const PRECACHE_URLS = [
    './',
    './index.html',
    './html/phone-directory.html',
    './html/lab-test-query.html',
    './html/weekend-scheduler.html',
    './html/egfr-calc.html'
];

// 安装事件 - 预缓存核心资源
self.addEventListener('install', function(event) {
    event.waitUntil(
        caches.open(CACHE_NAME).then(function(cache) {
            return cache.addAll(PRECACHE_URLS);
        }).then(function() {
            return self.skipWaiting();
        })
    );
});

// 激活事件 - 清理旧缓存
self.addEventListener('activate', function(event) {
    event.waitUntil(
        caches.keys().then(function(cacheNames) {
            return Promise.all(
                cacheNames.filter(function(name) {
                    return name !== CACHE_NAME;
                }).map(function(name) {
                    return caches.delete(name);
                })
            );
        }).then(function() {
            return self.clients.claim();
        })
    );
});

// 请求拦截 - 缓存优先策略
self.addEventListener('fetch', function(event) {
    // 跳过非 GET 请求和第三方统计/分析请求
    if (event.request.method !== 'GET') return;
    var url = new URL(event.request.url);
    if (url.hostname !== self.location.hostname) return;

    event.respondWith(
        caches.match(event.request).then(function(cached) {
            // 同时发起网络请求更新缓存
            var fetchPromise = fetch(event.request).then(function(response) {
                if (response && response.status === 200) {
                    var clone = response.clone();
                    caches.open(CACHE_NAME).then(function(cache) {
                        cache.put(event.request, clone);
                    });
                }
                return response;
            }).catch(function() {
                // 网络失败时回退到缓存
                return cached;
            });

            return cached || fetchPromise;
        })
    );
});
