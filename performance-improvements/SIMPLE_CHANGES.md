# Simple Performance Changes - Apply to Your Existing Files

Instead of replacing entire files, make these small changes to your existing backend files:

## 1. Update backend/app.py

### Add GZip compression (Line ~20)

```python
from fastapi.middleware.gzip import GZipMiddleware

# Add this after creating app
app.add_middleware(GZipMiddleware, minimum_size=1000)
```

### Add cache headers to file responses

Find your existing file serving functions and add cache headers:

```python
@app.get("/favicon.ico")
async def serve_favicon_ico():
    favicon_path = STATIC_DIR / "favicon.ico"
    if favicon_path.exists():
        response = FileResponse(favicon_path)
        response.headers["Cache-Control"] = "public, max-age=86400"  # <-- ADD THIS
        return response
```

Do the same for:
- `/style.css` - max-age=3600
- `/{filename}.html` - max-age=300
- `/manifest.json` - max-age=3600

### Add service-worker.js endpoint

```python
@app.get("/service-worker.js")
async def serve_service_worker():
    sw_path = STATIC_DIR / "service-worker.js"
    if sw_path.exists():
        response = FileResponse(sw_path, media_type="application/javascript")
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        return response
    return {"error": "service-worker.js not found"}
```

---

## 2. Update backend/models.py

### Add indexes (after your class definitions)

```python
class Provider(Base):
    __tablename__ = "providers"
    id = Column(String, primary_key=True, index=True)
    name = Column(String, nullable=False, index=True)  # <-- Add index=True
    email = Column(String, nullable=True)
    # ... rest of your code

class Signup(Base):
    __tablename__ = "signups"
    id = Column(Integer, primary_key=True, index=True)
    provider_id = Column(String, ForeignKey("providers.id"), nullable=False, index=True)  # <-- Add index=True
    shift_id = Column(Integer, ForeignKey("shifts.id"), nullable=False, index=True)  # <-- Add index=True
    # ... rest of your code
```

### Optimize SQLite in init_db() function

Add this to your existing `init_db()` function:

```python
def init_db():
    print("[Database] Creating tables and indexes...")
    Base.metadata.create_all(bind=engine)
    
    # ADD THESE OPTIMIZATIONS
    with engine.connect() as conn:
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA cache_size=-20000")  # 20MB cache
        conn.execute("PRAGMA mmap_size=10485760")  # 10MB memory-mapped
        conn.execute("PRAGMA synchronous=NORMAL")
        conn.execute("ANALYZE")
        conn.commit()
    
    print("[Database] Initialization complete with optimizations")
```

---

## 3. Copy service-worker.js

Just copy the `service-worker.js` file from the `performance-improvements/` folder to your project root.

---

## 4. Add to HTML files

Add this to ALL your HTML files (before closing `</body>` tag):

```html
<script>
// Service Worker Registration
if ('serviceWorker' in navigator) {
  window.addEventListener('load', async () => {
    try {
      await navigator.serviceWorker.register('/service-worker.js');
      console.log('✅ Service Worker registered');
    } catch (error) {
      console.error('❌ SW failed:', error);
    }
  });
}
</script>
```

---

## That's It!

These simple changes will give you:
- ✅ GZip compression (smaller file sizes)
- ✅ Browser caching (faster repeat loads)
- ✅ Database indexes (faster queries)
- ✅ SQLite optimizations (better performance)
- ✅ Offline support (via service worker)

**Deploy:**
```bash
fly deploy
```

**Verify:**
- Open DevTools → Application → Service Workers
- Should see "service-worker.js" activated
