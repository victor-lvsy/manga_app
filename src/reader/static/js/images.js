/**
 * Images Module
 * Handles image loading, error handling, and lazy loading
 */

class ImageManager {
    constructor() {
        this.placeholderCache = new Map();
        this.lazyImages = [];
        this.init();
    }

    init() {
        // Wait for DOM to be ready
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', () => this.setupImages());
        } else {
            this.setupImages();
        }
    }

    setupImages() {
        this.setupCoverImages();
        this.setupLazyLoading();
        this.setupImageErrorHandling();
    }

    setupCoverImages() {
        const coverImages = document.querySelectorAll('.cover-image, .mobile-cover-image');

        coverImages.forEach(img => {
            // Add loading state
            img.classList.add('loading');

            // Handle load success
            img.addEventListener('load', () => {
                img.classList.remove('loading');
                img.classList.add('loaded');
            });

            // Handle load error with fallback
            img.addEventListener('error', (e) => {
                this.handleImageError(e.target);
            });
        });
    }

    handleImageError(img) {
        const mangaName = img.alt.split(' - ')[0] || 'Manga';
        const encodedName = encodeURIComponent(mangaName);

        // Determine placeholder size based on class
        let width, height;
        if (img.classList.contains('cover-image')) {
            width = 300;
            height = 400;
        } else if (img.classList.contains('mobile-cover-image')) {
            width = 250;
            height = 350;
        } else {
            width = 200;
            height = 280;
        }

        const placeholderUrl = `https://via.placeholder.com/${width}x${height}/2c3e50/ecf0f1?text=${encodedName}`;

        // Cache the placeholder to avoid multiple requests
        if (!this.placeholderCache.has(placeholderUrl)) {
            this.placeholderCache.set(placeholderUrl, true);
        }

        img.src = placeholderUrl;
        img.classList.remove('loading');
        img.classList.add('error');

        console.warn(`Cover image failed to load for ${mangaName}, using placeholder`);
    }

    setupLazyLoading() {
        // Check if IntersectionObserver is supported
        if ('IntersectionObserver' in window) {
            const imageObserver = new IntersectionObserver((entries, observer) => {
                entries.forEach(entry => {
                    if (entry.isIntersecting) {
                        const img = entry.target;
                        this.loadImage(img);
                        observer.unobserve(img);
                    }
                });
            });

            // Observe all images with data-src attribute
            const lazyImages = document.querySelectorAll('img[data-src]');
            lazyImages.forEach(img => imageObserver.observe(img));
        } else {
            // Fallback for browsers without IntersectionObserver
            const lazyImages = document.querySelectorAll('img[data-src]');
            lazyImages.forEach(img => this.loadImage(img));
        }
    }

    loadImage(img) {
        if (img.dataset.src) {
            img.src = img.dataset.src;
            img.removeAttribute('data-src');
        }
    }

    setupImageErrorHandling() {
        // Global error handler for all images
        document.addEventListener('error', (e) => {
            if (e.target.tagName === 'IMG') {
                this.handleImageError(e.target);
            }
        }, true);
    }

    // Method to preload images
    preloadImage(src) {
        return new Promise((resolve, reject) => {
            const img = new Image();
            img.onload = () => resolve(img);
            img.onerror = () => reject(new Error(`Failed to load image: ${src}`));
            img.src = src;
        });
    }

    // Method to get image dimensions
    getImageDimensions(src) {
        return new Promise((resolve, reject) => {
            const img = new Image();
            img.onload = () => {
                resolve({
                    width: img.naturalWidth,
                    height: img.naturalHeight
                });
            };
            img.onerror = () => reject(new Error(`Failed to load image: ${src}`));
            img.src = src;
        });
    }
}

// Initialize image manager when script loads
const imageManager = new ImageManager();

// Export for use in other modules
window.ImageManager = ImageManager;
