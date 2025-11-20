# ⚡ Performance Improvements Quick Reference

## 🎯 Common API Patterns

### GET Request (with caching)
```javascript
const data = await api.fetch('/api/endpoint', {}, {
  ttl: 5 * 60 * 1000  // Cache for 5 minutes
});
```

### POST Request (no caching)
```javascript
const result = await api.fetch('/api/signup', {
  method: 'POST',
  body: { key: 'value' }
}, {
  cacheable: false
});
```

### Prefetch Multiple Endpoints
```javascript
await api.prefetch([
  '/api/providers',
  '/api/signups?month=2025-11',
  '/api/assignments'
], {
  ttl: 10 * 60 * 1000
});
```

### Invalidate Cache
```javascript
await api.invalidate('/api/providers');
```

---

## 🐛 Debug Commands

### Check Cache Status
```javascript
console.log(cache.getStats());
// Output: { memorySize: 10, memoryActive: 8, memoryExpired: 2 }
```

### View Service Worker
```javascript
navigator.serviceWorker.getRegistrations()
  .then(regs => console.log('Registered:', regs));
```

### Clear All Caches
```javascript
await cache.clear();
caches.keys().then(names => names.forEach(name => caches.delete(name)));
```

### Force Cache Refresh
```javascript
const data = await api.fetch('/api/providers', {}, {
  forceRefresh: true
});
```

---

## 📊 Cache TTL Guidelines

| Data Type | Recommended TTL |
|-----------|------------------|
| Provider list | 1 hour (3600000ms) |
| Signups (current month) | 5 minutes (300000ms) |
| Assignments | 10 minutes (600000ms) |
| Static assets | 24 hours (86400000ms) |

---

## 📱 PWA Features

### Install Prompt
```javascript
let deferredPrompt;

window.addEventListener('beforeinstallprompt', (e) => {
  e.preventDefault();
  deferredPrompt = e;
  showInstallButton();
});

function showInstallButton() {
  const btn = document.getElementById('installBtn');
  btn.style.display = 'block';
  btn.onclick = () => deferredPrompt.prompt();
}
```

### Offline Detection
```javascript
window.addEventListener('offline', () => {
  console.log('⚠️ Offline mode');
});

window.addEventListener('online', () => {
  console.log('✅ Back online');
});
```

---

## ⚠️ Common Issues

### Service Worker Not Working
- Check HTTPS is enabled (required)
- Verify file at `/service-worker.js`
- Clear browser cache completely

### Cache Not Persisting
- Check IndexedDB is enabled
- Verify browser storage quota
- Clear expired entries: `cache.clearExpired()`

### Slow First Load
- Normal! Subsequent loads will be fast
- Use prefetching to warm cache

---

## ✅ Verification Checklist

- [ ] Open DevTools → Application → Service Workers
- [ ] See "service-worker.js" with status "activated"
- [ ] Open Application → Cache Storage
- [ ] See caches: `pccm-v1.2-static`, `pccm-v1.2-api`
- [ ] Test offline mode (Network tab → Offline)
- [ ] Page still loads from cache
- [ ] Check console for cache hit logs

---

## 🔧 Fly.io Commands

```bash
# View logs
fly logs --tail

# SSH into container
fly ssh console

# Check database
sqlite3 /data/moonlighter.db
.schema

# Restart app
fly apps restart
```
