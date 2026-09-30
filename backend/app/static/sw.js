// Coach Studio service worker — makes the app installable (Android/Chrome +
// iOS) and lets the shell load offline. Live data still needs a connection;
// API calls are never cached.
const CACHE = 'coach-studio-v2';
const APP_SHELL = [
	'/',
	'/static/manifest.webmanifest',
	'/static/icon-192.png',
	'/static/icon-512.png',
	'/static/apple-touch-icon.png',
];

self.addEventListener('install', (event) => {
	event.waitUntil(
		caches.open(CACHE)
			.then((cache) => cache.addAll(APP_SHELL))
			.then(() => self.skipWaiting())
	);
});

self.addEventListener('activate', (event) => {
	event.waitUntil(
		caches.keys()
			.then((keys) => Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k))))
			.then(() => self.clients.claim())
	);
});

self.addEventListener('fetch', (event) => {
	const req = event.request;
	if (req.method !== 'GET') return;

	const url = new URL(req.url);
	// Only our own origin, and never touch the API (auth + live data).
	if (url.origin !== self.location.origin) return;
	if (url.pathname.startsWith('/api/')) return;

	// Page loads: network-first so the app updates when online, falling back to
	// the cached shell when offline.
	if (req.mode === 'navigate') {
		event.respondWith(
			fetch(req)
				.then((res) => {
					const copy = res.clone();
					caches.open(CACHE).then((cache) => cache.put('/', copy)).catch(() => {});
					return res;
				})
				.catch(() => caches.match('/').then((cached) => cached || caches.match(req)))
		);
		return;
	}

	// Other same-origin assets (icons, images, manifest): stale-while-revalidate.
	event.respondWith(
		caches.match(req).then((cached) => {
			const network = fetch(req)
				.then((res) => {
					if (res && res.status === 200) {
						const copy = res.clone();
						caches.open(CACHE).then((cache) => cache.put(req, copy)).catch(() => {});
					}
					return res;
				})
				.catch(() => cached);
			return cached || network;
		})
	);
});

// ---- Web Push: show a notification, and focus/open the app on click ----
self.addEventListener('push', (event) => {
	let data = {};
	try { data = event.data ? event.data.json() : {}; } catch (e) {}
	const title = data.title || 'Coach Studio';
	const options = {
		body: data.body || 'New message',
		icon: '/static/icon-192.png',
		badge: '/static/icon-192.png',
		data: { url: data.url || '/' },
	};
	event.waitUntil(self.registration.showNotification(title, options));
});

self.addEventListener('notificationclick', (event) => {
	event.notification.close();
	const url = (event.notification.data && event.notification.data.url) || '/';
	event.waitUntil(
		clients.matchAll({ type: 'window', includeUncontrolled: true }).then((wins) => {
			for (const w of wins) {
				if ('focus' in w) { w.focus(); if (w.navigate) { try { w.navigate(url); } catch (e) {} } return; }
			}
			if (clients.openWindow) return clients.openWindow(url);
		})
	);
});
