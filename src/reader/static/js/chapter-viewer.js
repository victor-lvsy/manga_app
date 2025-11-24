/**
 * Chapter Viewer Module
 * Handles chapter reading functionality, keyboard shortcuts, and navigation
 */

class ChapterViewer {
    constructor() {
        this.mangaId = null;
        this.chapterPath = null;
        this.prevChapter = null;
        this.nextChapter = null;
        this.images = [];
        this.currentImageIndex = 0;
        this.isFullscreen = false;

        this.init();
    }

    init() {
        // Wait for DOM to be ready
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', () => this.setupChapter());
        } else {
            this.setupChapter();
        }
    }

    setupChapter() {
        this.extractChapterData();
        this.setupKeyboardShortcuts();
        this.setupImageLoading();
        this.setupFullscreenSupport();
    }

    extractChapterData() {
        // Extract data from the page
        const currentUrl = window.location.pathname;
        const urlParts = currentUrl.split('/');

        this.mangaId = urlParts[1];
        this.chapterPath = urlParts[3];

        // Get navigation links
        const prevLink = document.querySelector('a[href*="prev_chapter"]');
        const nextLink = document.querySelector('a[href*="next_chapter"]');

        this.prevChapter = prevLink ? prevLink.href : null;
        this.nextChapter = nextLink ? nextLink.href : null;

        // Get all images
        this.images = Array.from(document.querySelectorAll('.page img'));
    }

    setupKeyboardShortcuts() {
        document.addEventListener('keydown', (e) => {
            // Don't trigger shortcuts when typing in inputs
            if (e.target && (e.target.tagName === 'INPUT' || e.target.isContentEditable)) {
                return;
            }

            switch (e.key) {
                case 'ArrowLeft':
                    this.navigateToPreviousChapter();
                    break;
                case 'ArrowRight':
                    this.navigateToNextChapter();
                    break;
                case 't':
                case 'T':
                    this.scrollToTop();
                    break;
                case 'b':
                case 'B':
                    this.scrollToBottom();
                    break;
                case 'f':
                case 'F':
                    this.toggleFullscreen();
                    break;
                case 'Escape':
                    this.exitFullscreen();
                    break;
                case ' ':
                    e.preventDefault();
                    this.toggleAutoScroll();
                    break;
                case 'Home':
                    this.scrollToTop();
                    break;
                case 'End':
                    this.scrollToBottom();
                    break;
            }
        });
    }

    setupImageLoading() {
        const images = document.querySelectorAll('.page img');

        images.forEach((img, index) => {
            // Add loading state
            img.classList.add('loading');

            // Handle load success
            img.addEventListener('load', () => {
                img.classList.remove('loading');
                img.classList.add('loaded');
            });

            // Handle load error
            img.addEventListener('error', () => {
                img.classList.remove('loading');
                img.classList.add('error');
                console.warn(`Failed to load image: ${img.src}`);
            });

            // Track image visibility
            this.setupImageVisibilityTracking(img, index);
        });
    }

    setupImageVisibilityTracking(img, index) {
        if ('IntersectionObserver' in window) {
            const observer = new IntersectionObserver((entries) => {
                entries.forEach(entry => {
                    if (entry.isIntersecting) {
                        this.currentImageIndex = index;
                    }
                });
            }, {
                threshold: 0.5
            });

            observer.observe(img);
        }
    }

    setupFullscreenSupport() {
        // Listen for fullscreen changes
        document.addEventListener('fullscreenchange', () => {
            this.isFullscreen = !!document.fullscreenElement;
            this.updateFullscreenUI();
        });
    }

    navigateToPreviousChapter() {
        if (this.prevChapter) {
            window.location.href = this.prevChapter;
        } else {
            Utils.showNotification('Premier chapitre', 'info');
        }
    }

    navigateToNextChapter() {
        if (this.nextChapter) {
            window.location.href = this.nextChapter;
        } else {
            Utils.showNotification('Dernier chapitre', 'info');
        }
    }

    scrollToTop() {
        window.scrollTo({
            top: 0,
            behavior: 'smooth'
        });
    }

    scrollToBottom() {
        window.scrollTo({
            top: document.body.scrollHeight,
            behavior: 'smooth'
        });
    }

    toggleFullscreen() {
        if (!this.isFullscreen) {
            this.enterFullscreen();
        } else {
            this.exitFullscreen();
        }
    }

    enterFullscreen() {
        const container = document.querySelector('.chapter-container');
        if (container && container.requestFullscreen) {
            container.requestFullscreen().then(() => {
                this.isFullscreen = true;
                this.updateFullscreenUI();
            }).catch(err => {
                console.warn('Failed to enter fullscreen:', err);
            });
        }
    }

    exitFullscreen() {
        if (document.exitFullscreen) {
            document.exitFullscreen().then(() => {
                this.isFullscreen = false;
                this.updateFullscreenUI();
            });
        }
    }

    updateFullscreenUI() {
        const container = document.querySelector('.chapter-container');
        if (container) {
            container.classList.toggle('fullscreen', this.isFullscreen);
        }
    }

    toggleAutoScroll() {
        // Toggle auto-scroll functionality
        if (this.autoScrollInterval) {
            clearInterval(this.autoScrollInterval);
            this.autoScrollInterval = null;
            Utils.showNotification('Auto-scroll arrêté', 'info');
        } else {
            this.startAutoScroll();
        }
    }

    startAutoScroll() {
        const scrollSpeed = 1; // pixels per interval
        const scrollInterval = 50; // milliseconds

        this.autoScrollInterval = setInterval(() => {
            window.scrollBy(0, scrollSpeed);

            // Stop at bottom
            if (window.innerHeight + window.scrollY >= document.body.offsetHeight) {
                this.toggleAutoScroll();
            }
        }, scrollInterval);

        Utils.showNotification('Auto-scroll démarré', 'info');
    }


    // Public API methods
    getCurrentChapter() {
        return {
            mangaId: this.mangaId,
            chapterPath: this.chapterPath,
            hasNext: !!this.nextChapter,
            hasPrev: !!this.prevChapter
        };
    }

    goToImage(index) {
        if (index >= 0 && index < this.images.length) {
            this.images[index].scrollIntoView({ behavior: 'smooth' });
            this.currentImageIndex = index;
        }
    }
}

// Initialize chapter viewer when script loads
const chapterViewer = new ChapterViewer();

// Export for use in other modules
window.ChapterViewer = ChapterViewer;
