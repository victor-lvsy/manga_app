/**
 * Main Application Module
 * Initializes all modules and handles global application state
 */

class MangaReaderApp {
    constructor() {
        this.modules = {};
        this.isInitialized = false;
        this.init();
    }

    init() {
        // Wait for DOM to be ready
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', () => this.initializeApp());
        } else {
            this.initializeApp();
        }
    }

    initializeApp() {
        if (this.isInitialized) return;

        try {
            this.initializeModules();
            this.setupGlobalEventListeners();
            this.setupErrorHandling();
            this.isInitialized = true;

            console.log('MangaReader App initialized successfully');
        } catch (error) {
            console.error('Failed to initialize MangaReader App:', error);
        }
    }

    initializeModules() {
        // Initialize core modules
        this.modules.navigation = window.NavigationManager ? new NavigationManager() : null;
        this.modules.images = window.ImageManager ? new ImageManager() : null;

        // Initialize page-specific modules
        this.initializePageModules();
    }

    initializePageModules() {
        const currentPage = this.getCurrentPage();

        switch (currentPage) {
            case 'manga-list':
                this.initializeMangaListPage();
                break;
            case 'manga-detail':
                this.initializeMangaDetailPage();
                break;
            case 'chapter-viewer':
                this.initializeChapterViewerPage();
                break;
            default:
                console.log('No specific page modules to initialize');
        }
    }

    getCurrentPage() {
        const path = window.location.pathname;

        if (path === '/') return 'manga-list';
        if (path.match(/^\/manga\/[^\/]+$/)) return 'manga-detail';
        if (path.match(/^\/[^\/]+\/chapter\//)) return 'chapter-viewer';

        return 'unknown';
    }

    initializeMangaListPage() {
        // Initialize manga list specific functionality
        this.setupMangaCardInteractions();
        this.setupMangaSearch();
    }

    initializeMangaDetailPage() {
        // Initialize manga detail specific functionality
        this.setupMangaDetailInteractions();
    }

    initializeChapterViewerPage() {
        // Initialize chapter viewer specific functionality
        this.setupChapterViewerInteractions();
    }

    setupMangaCardInteractions() {
        const mangaCards = document.querySelectorAll('.manga-card');

        mangaCards.forEach(card => {
            // Add hover effects
            card.addEventListener('mouseenter', () => {
                card.style.transform = 'translateY(-5px)';
            });

            card.addEventListener('mouseleave', () => {
                card.style.transform = 'translateY(0)';
            });

            // Add click tracking (for analytics if needed)
            card.addEventListener('click', (e) => {
                const link = card.querySelector('a[href*="/manga/"]');
                if (link && !e.target.closest('.manga-actions')) {
                    // Track manga view
                    this.trackEvent('manga_view', {
                        manga_id: link.href.split('/').pop(),
                        manga_name: card.querySelector('.manga-title')?.textContent
                    });
                }
            });
        });
    }

    setupMangaSearch() {
        // Add search functionality if search input exists
        const searchInput = document.querySelector('#manga-search');
        if (searchInput) {
            searchInput.addEventListener('input', Utils.debounce((e) => {
                this.filterMangas(e.target.value);
            }, 300));
        }
    }

    filterMangas(searchTerm) {
        const mangaCards = document.querySelectorAll('.manga-card');
        const term = searchTerm.toLowerCase();

        mangaCards.forEach(card => {
            const title = card.querySelector('.manga-title')?.textContent.toLowerCase() || '';
            const isVisible = title.includes(term);

            card.style.display = isVisible ? 'block' : 'none';
        });
    }

    setupMangaDetailInteractions() {
        // Setup manga detail page interactions
        this.setupActionButtons();
    }

    setupChapterViewerInteractions() {
        // Setup chapter viewer interactions
        this.setupChapterNavigation();
        this.setupKeyboardShortcuts();
    }

    setupActionButtons() {
        const actionButtons = document.querySelectorAll('.action-buttons .btn, .mobile-action-buttons .btn');

        actionButtons.forEach(button => {
            button.addEventListener('click', (e) => {
                const action = button.textContent.trim();
                this.trackEvent('button_click', {
                    action: action,
                    page: this.getCurrentPage()
                });
            });
        });
    }

    setupChapterNavigation() {
        // Setup chapter navigation if on chapter page
        const prevButton = document.querySelector('.prev-chapter');
        const nextButton = document.querySelector('.next-chapter');

        if (prevButton) {
            prevButton.addEventListener('click', () => {
                this.trackEvent('chapter_navigation', { direction: 'previous' });
            });
        }

        if (nextButton) {
            nextButton.addEventListener('click', () => {
                this.trackEvent('chapter_navigation', { direction: 'next' });
            });
        }
    }

    setupKeyboardShortcuts() {
        // Add keyboard shortcuts for chapter navigation
        document.addEventListener('keydown', (e) => {
            if (this.getCurrentPage() === 'chapter-viewer') {
                switch (e.key) {
                    case 'ArrowLeft':
                        const prevChapter = document.querySelector('.prev-chapter');
                        if (prevChapter) prevChapter.click();
                        break;
                    case 'ArrowRight':
                        const nextChapter = document.querySelector('.next-chapter');
                        if (nextChapter) nextChapter.click();
                        break;
                    case 'Escape':
                        // Return to manga detail
                        const mangaId = window.location.pathname.split('/')[1];
                        if (mangaId) {
                            window.location.href = `/manga/${mangaId}`;
                        }
                        break;
                }
            }
        });
    }

    setupGlobalEventListeners() {
        // Handle window resize
        window.addEventListener('resize', Utils.debounce(() => {
            this.handleResize();
        }, 250));

        // Handle page visibility changes
        document.addEventListener('visibilitychange', () => {
            this.handleVisibilityChange();
        });

        // Handle online/offline status
        window.addEventListener('online', () => {
            Utils.showNotification('Connection restored', 'success');
        });

        window.addEventListener('offline', () => {
            Utils.showNotification('Connection lost', 'warning', 0);
        });
    }

    setupErrorHandling() {
        // Global error handler
        window.addEventListener('error', (e) => {
            console.error('Global error:', e.error);
            this.trackEvent('error', {
                message: e.message,
                filename: e.filename,
                lineno: e.lineno,
                colno: e.colno
            });
        });

        // Unhandled promise rejection handler
        window.addEventListener('unhandledrejection', (e) => {
            console.error('Unhandled promise rejection:', e.reason);
            this.trackEvent('promise_rejection', {
                reason: e.reason?.toString()
            });
        });
    }

    handleResize() {
        // Close mobile menu if open and screen becomes large
        if (Utils.getDeviceType() !== 'mobile' && this.modules.navigation?.isMenuOpen) {
            this.modules.navigation.closeMenu();
        }
    }

    handleVisibilityChange() {
        if (document.hidden) {
            // Page is hidden, pause any ongoing operations
            this.pauseOperations();
        } else {
            // Page is visible, resume operations
            this.resumeOperations();
        }
    }

    pauseOperations() {
        // Pause any ongoing operations when page is hidden
        console.log('Page hidden, pausing operations');
    }

    resumeOperations() {
        // Resume operations when page becomes visible
        console.log('Page visible, resuming operations');
    }

    trackEvent(eventName, data = {}) {
        // Simple event tracking (can be extended with analytics service)
        console.log('Event tracked:', eventName, data);

        // Store in localStorage for debugging
        const events = Utils.storage.get('tracked_events', []);
        events.push({
            timestamp: new Date().toISOString(),
            event: eventName,
            data: data
        });

        // Keep only last 100 events
        if (events.length > 100) {
            events.splice(0, events.length - 100);
        }

        Utils.storage.set('tracked_events', events);
    }

    // Public API methods
    getModule(name) {
        return this.modules[name];
    }

    isReady() {
        return this.isInitialized;
    }
}

// Initialize the application
const app = new MangaReaderApp();

// Export for global access
window.MangaReaderApp = MangaReaderApp;
window.app = app;
