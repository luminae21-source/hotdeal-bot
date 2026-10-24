var V='hdp-30ec379018',PRE=['/','/icons/icon-192.png?v=2','/icons/icon-512.png?v=2','/icons/apple-touch-icon.png?v=2','/favicon.ico?v=2'];
self.addEventListener('install',function(e){e.waitUntil(caches.open(V).then(function(c){return c.addAll(PRE)}).then(function(){return self.skipWaiting()}))});
self.addEventListener('activate',function(e){e.waitUntil(caches.keys().then(function(ks){return Promise.all(ks.filter(function(k){return k!==V}).map(function(k){return caches.delete(k)}))}).then(function(){return self.clients.claim()}))});
self.addEventListener('fetch',function(e){var r=e.request,u=new URL(r.url);
if(r.method!=='GET'||u.origin!==location.origin)return;
if(/^\/icons\/|^\/favicon\.ico$|\.(css|woff2?|otf|ttf)$/.test(u.pathname)){e.respondWith(caches.match(r).then(function(c){return c||fetch(r).then(function(res){if(res.ok){var x=res.clone();caches.open(V).then(function(k){k.put(r,x)})}return res})}));return}
e.respondWith(fetch(r).then(function(res){if(res.ok&&r.mode==='navigate'){var x=res.clone();caches.open(V).then(function(k){k.put(r,x)})}return res}).catch(function(){return caches.match(r).then(function(c){return c||(r.mode==='navigate'?caches.match('/'):Response.error())})}))});
