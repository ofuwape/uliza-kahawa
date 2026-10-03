// Offline cache: everything the app needs, saved on first load. Online: fetch fresh and refresh the saved copy;
// offline: serve the saved copy. So updates show up, and it still works with no connection.
const CACHE = 'uliza-kahawa-v11';
const FILES = ['./', 'index.html', 'app.css', 'app.js', 'model.js', 'channels.js', 'briefing.sample.json', '../models/model.json', '../answers/answers.built.json'];

// The recorded answers are listed in answers/audio/index.json; save them too so Listen works offline.
self.addEventListener('install', e => e.waitUntil(caches.open(CACHE).then(async c => {
  await c.addAll(FILES);
  try {
    const idx = await (await fetch('../answers/audio/index.json')).json();
    await c.addAll(['../answers/audio/index.json', ...Object.values(idx.files).flatMap(v => Object.values(v)).map(f => '../answers/' + f)]);
  } catch (err) { /* audio is optional */ }
}).then(() => self.skipWaiting())));
self.addEventListener('activate', e => e.waitUntil(
  caches.keys().then(ks => Promise.all(ks.filter(k => k !== CACHE).map(k => caches.delete(k)))).then(() => self.clients.claim())));
self.addEventListener('fetch', e => {
  if (e.request.method !== 'GET') return;
  e.respondWith(fetch(e.request).then(res => {
    const copy = res.clone();
    caches.open(CACHE).then(c => c.put(e.request, copy));
    return res;
  }).catch(() => caches.match(e.request, {ignoreSearch: true})));
});
