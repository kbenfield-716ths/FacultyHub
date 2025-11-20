/**
 * CacheManager - Client-side caching layer for Moonlighter Web App
 * 
 * Provides intelligent caching for:
 * - Provider data (frequently accessed, changes rarely)
 * - Schedule data (accessed often, may change during scheduling)
 * - Period data (static within a period)
 * - Static content (CSS, JS, images)
 * 
 * Features:
 * - TTL-based expiration
 * - Cache invalidation
 * - Size limits
 * - LRU eviction
 * - Offline support
 */

class CacheManager {
  constructor(options = {}) {
    this.storageKey = options.storageKey || 'moonlighter_cache';
    this.maxSize = options.maxSize || 5 * 1024 * 1024; // 5MB default
    this.defaultTTL = options.defaultTTL || 5 * 60 * 1000; // 5 minutes default
    
    // Cache configuration by type
    this.cacheConfig = {
      provider: { ttl: 30 * 60 * 1000, priority: 'high' },      // 30 min (changes rarely)
      schedule: { ttl: 2 * 60 * 1000, priority: 'medium' },      // 2 min (changes during scheduling)
      period: { ttl: 60 * 60 * 1000, priority: 'high' },         // 1 hour (static within period)
      static: { ttl: 24 * 60 * 60 * 1000, priority: 'high' },    // 24 hours (CSS, JS, images)
      api: { ttl: 5 * 60 * 1000, priority: 'medium' }            // 5 min (general API calls)
    };
    
    this.init();
  }
  
  /**
   * Initialize cache manager
   */
  init() {
    try {
      // Check if localStorage is available
      if (!this.isStorageAvailable()) {
        console.warn('CacheManager: localStorage not available, using memory cache');
        this.memoryCache = new Map();
        this.useMemory = true;
      } else {
        this.useMemory = false;
        // Clean up expired entries on init
        this.cleanup();
      }
    } catch (error) {
      console.error('CacheManager init error:', error);
      this.memoryCache = new Map();
      this.useMemory = true;
    }
  }
  
  /**
   * Check if localStorage is available
   */
  isStorageAvailable() {
    try {
      const test = '__storage_test__';
      localStorage.setItem(test, test);
      localStorage.removeItem(test);
      return true;
    } catch (e) {
      return false;
    }
  }
  
  /**
   * Get cached item
   * @param {string} key - Cache key
   * @returns {any} Cached value or null
   */
  get(key) {
    try {
      if (this.useMemory) {
        const item = this.memoryCache.get(key);
        if (!item) return null;
        
        // Check expiration
        if (Date.now() > item.expires) {
          this.memoryCache.delete(key);
          return null;
        }
        
        // Update access time for LRU
        item.lastAccess = Date.now();
        return item.value;
      }
      
      // localStorage
      const cache = this.getCache();
      const item = cache[key];
      
      if (!item) return null;
      
      // Check expiration
      if (Date.now() > item.expires) {
        delete cache[key];
        this.saveCache(cache);
        return null;
      }
      
      // Update access time for LRU
      item.lastAccess = Date.now();
      this.saveCache(cache);
      
      return item.value;
    } catch (error) {
      console.error('CacheManager get error:', error);
      return null;
    }
  }
  
  /**
   * Set cache item
   * @param {string} key - Cache key
   * @param {any} value - Value to cache
   * @param {object} options - Cache options (ttl, type)
   */
  set(key, value, options = {}) {
    try {
      const type = options.type || 'api';
      const config = this.cacheConfig[type] || this.cacheConfig.api;
      const ttl = options.ttl || config.ttl;
      
      const item = {
        value: value,
        expires: Date.now() + ttl,
        created: Date.now(),
        lastAccess: Date.now(),
        type: type,
        priority: config.priority
      };
      
      if (this.useMemory) {
        this.memoryCache.set(key, item);
        this.enforceMemoryLimit();
        return;
      }
      
      // localStorage
      const cache = this.getCache();
      cache[key] = item;
      
      // Check size and enforce limit
      if (this.getCacheSize(cache) > this.maxSize) {
        this.evictOldest(cache);
      }
      
      this.saveCache(cache);
    } catch (error) {
      console.error('CacheManager set error:', error);
    }
  }
  
  /**
   * Delete cached item
   * @param {string} key - Cache key
   */
  delete(key) {
    try {
      if (this.useMemory) {
        this.memoryCache.delete(key);
        return;
      }
      
      const cache = this.getCache();
      delete cache[key];
      this.saveCache(cache);
    } catch (error) {
      console.error('CacheManager delete error:', error);
    }
  }
  
  /**
   * Clear all cache or by type
   * @param {string} type - Optional type to clear
   */
  clear(type = null) {
    try {
      if (this.useMemory) {
        if (type) {
          for (const [key, item] of this.memoryCache.entries()) {
            if (item.type === type) {
              this.memoryCache.delete(key);
            }
          }
        } else {
          this.memoryCache.clear();
        }
        return;
      }
      
      if (type) {
        const cache = this.getCache();
        Object.keys(cache).forEach(key => {
          if (cache[key].type === type) {
            delete cache[key];
          }
        });
        this.saveCache(cache);
      } else {
        localStorage.removeItem(this.storageKey);
      }
    } catch (error) {
      console.error('CacheManager clear error:', error);
    }
  }
  
  /**
   * Get cache from localStorage
   */
  getCache() {
    try {
      const data = localStorage.getItem(this.storageKey);
      return data ? JSON.parse(data) : {};
    } catch (error) {
      console.error('CacheManager getCache error:', error);
      return {};
    }
  }
  
  /**
   * Save cache to localStorage
   */
  saveCache(cache) {
    try {
      localStorage.setItem(this.storageKey, JSON.stringify(cache));
    } catch (error) {
      console.error('CacheManager saveCache error:', error);
      // If quota exceeded, try to free up space
      if (error.name === 'QuotaExceededError') {
        this.evictOldest(cache, 0.5); // Remove 50% of entries
        try {
          localStorage.setItem(this.storageKey, JSON.stringify(cache));
        } catch (retryError) {
          console.error('CacheManager saveCache retry error:', retryError);
        }
      }
    }
  }
  
  /**
   * Calculate cache size
   */
  getCacheSize(cache) {
    try {
      return new Blob([JSON.stringify(cache)]).size;
    } catch (error) {
      console.error('CacheManager getCacheSize error:', error);
      return 0;
    }
  }
  
  /**
   * Evict oldest entries based on LRU
   * @param {object} cache - Cache object
   * @param {number} percentage - Percentage of entries to remove (default 0.25)
   */
  evictOldest(cache, percentage = 0.25) {
    try {
      const entries = Object.entries(cache);
      
      // Sort by priority and last access time
      entries.sort((a, b) => {
        const priorityOrder = { high: 3, medium: 2, low: 1 };
        const aPriority = priorityOrder[a[1].priority] || 1;
        const bPriority = priorityOrder[b[1].priority] || 1;
        
        if (aPriority !== bPriority) {
          return aPriority - bPriority; // Lower priority first
        }
        
        return a[1].lastAccess - b[1].lastAccess; // Older access first
      });
      
      // Remove specified percentage
      const toRemove = Math.ceil(entries.length * percentage);
      for (let i = 0; i < toRemove; i++) {
        delete cache[entries[i][0]];
      }
    } catch (error) {
      console.error('CacheManager evictOldest error:', error);
    }
  }
  
  /**
   * Enforce memory cache size limit
   */
  enforceMemoryLimit() {
    try {
      const maxEntries = 100; // Maximum number of entries in memory
      
      if (this.memoryCache.size > maxEntries) {
        // Convert to array and sort by priority and access time
        const entries = Array.from(this.memoryCache.entries());
        entries.sort((a, b) => {
          const priorityOrder = { high: 3, medium: 2, low: 1 };
          const aPriority = priorityOrder[a[1].priority] || 1;
          const bPriority = priorityOrder[b[1].priority] || 1;
          
          if (aPriority !== bPriority) {
            return aPriority - bPriority;
          }
          
          return a[1].lastAccess - b[1].lastAccess;
        });
        
        // Remove oldest 25%
        const toRemove = Math.ceil(entries.length * 0.25);
        for (let i = 0; i < toRemove; i++) {
          this.memoryCache.delete(entries[i][0]);
        }
      }
    } catch (error) {
      console.error('CacheManager enforceMemoryLimit error:', error);
    }
  }
  
  /**
   * Clean up expired entries
   */
  cleanup() {
    try {
      if (this.useMemory) {
        const now = Date.now();
        for (const [key, item] of this.memoryCache.entries()) {
          if (now > item.expires) {
            this.memoryCache.delete(key);
          }
        }
        return;
      }
      
      const cache = this.getCache();
      const now = Date.now();
      let changed = false;
      
      Object.keys(cache).forEach(key => {
        if (now > cache[key].expires) {
          delete cache[key];
          changed = true;
        }
      });
      
      if (changed) {
        this.saveCache(cache);
      }
    } catch (error) {
      console.error('CacheManager cleanup error:', error);
    }
  }
  
  /**
   * Get cache statistics
   */
  getStats() {
    try {
      if (this.useMemory) {
        return {
          entries: this.memoryCache.size,
          size: 0,
          types: this.getTypeStats(Object.fromEntries(this.memoryCache))
        };
      }
      
      const cache = this.getCache();
      return {
        entries: Object.keys(cache).length,
        size: this.getCacheSize(cache),
        maxSize: this.maxSize,
        types: this.getTypeStats(cache)
      };
    } catch (error) {
      console.error('CacheManager getStats error:', error);
      return { entries: 0, size: 0, types: {} };
    }
  }
  
  /**
   * Get statistics by type
   */
  getTypeStats(cache) {
    const stats = {};
    
    Object.values(cache).forEach(item => {
      const type = item.type || 'unknown';
      if (!stats[type]) {
        stats[type] = { count: 0, size: 0 };
      }
      stats[type].count++;
    });
    
    return stats;
  }
  
  /**
   * Cached fetch wrapper
   * @param {string} url - URL to fetch
   * @param {object} options - Fetch options and cache options
   */
  async fetch(url, options = {}) {
    try {
      const cacheKey = this.getCacheKey(url, options);
      const cacheType = options.cacheType || 'api';
      
      // Check cache first
      const cached = this.get(cacheKey);
      if (cached) {
        console.log(`CacheManager: Cache hit for ${url}`);
        return cached;
      }
      
      // Fetch from network
      console.log(`CacheManager: Cache miss for ${url}, fetching...`);
      const response = await fetch(url, options);
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      
      const data = await response.json();
      
      // Cache the response
      this.set(cacheKey, data, { type: cacheType });
      
      return data;
    } catch (error) {
      console.error('CacheManager fetch error:', error);
      
      // Try to return stale cache on error
      const cacheKey = this.getCacheKey(url, options);
      const cache = this.getCache();
      if (cache[cacheKey]) {
        console.warn('CacheManager: Returning stale cache due to network error');
        return cache[cacheKey].value;
      }
      
      throw error;
    }
  }
  
  /**
   * Generate cache key from URL and options
   */
  getCacheKey(url, options = {}) {
    let key = url;
    
    // Include method if not GET
    if (options.method && options.method !== 'GET') {
      key += `_${options.method}`;
    }
    
    // Include body for POST/PUT
    if (options.body) {
      key += `_${JSON.stringify(options.body)}`;
    }
    
    return key;
  }
}

// Export for use
if (typeof module !== 'undefined' && module.exports) {
  module.exports = CacheManager;
}

// Global instance (optional)
if (typeof window !== 'undefined') {
  window.CacheManager = CacheManager;
  window.cacheManager = new CacheManager();
}
