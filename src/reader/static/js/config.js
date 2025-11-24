/**
 * Application Configuration
 * Centralized configuration for the MangaReader application
 */

const AppConfig = {
    // Application settings
    app: {
        name: 'MangaReader',
        version: '1.0.0',
        debug: true
    },

    // API endpoints
    api: {
        baseUrl: '',
        endpoints: {
            mangaList: '/',
            mangaDetail: '/manga/{id}',
            mangaCover: '/manga/{id}/cover',
            chapterView: '/{manga_id}/chapter/{chapter_path}',
            imageServe: '/manga/{manga_id}/image/{image_path}'
        }
    },

    // UI settings
    ui: {
        // Breakpoints (in pixels)
        breakpoints: {
            mobile: 768,
            tablet: 1024,
            desktop: 1200
        },

        // Animation durations (in milliseconds)
        animations: {
            fast: 150,
            normal: 300,
            slow: 500
        },

        // Notification settings
        notifications: {
            defaultDuration: 3000,
            maxVisible: 3
        },

        // Image settings
        images: {
            lazyLoadThreshold: 100, // pixels from viewport
            placeholderSizes: {
                cover: { width: 300, height: 400 },
                mobileCover: { width: 250, height: 350 },
                listCover: { width: 200, height: 280 }
            }
        }
    },

    // Feature flags
    features: {
        lazyLoading: true,
        keyboardShortcuts: true,
        offlineSupport: false,
        analytics: false,
        search: true,
        filters: false
    },

    // Local storage keys
    storage: {
        settings: 'manga_reader_settings',
        bookmarks: 'manga_reader_bookmarks',
        readingProgress: 'manga_reader_progress',
        trackedEvents: 'tracked_events'
    },

    // Default settings
    defaults: {
        theme: 'dark',
        language: 'fr',
        itemsPerPage: 20,
        autoPlay: false,
        showThumbnails: true,
        readingDirection: 'ltr'
    },

    // Error messages
    messages: {
        errors: {
            networkError: 'Erreur de connexion. Vérifiez votre connexion internet.',
            imageLoadError: 'Impossible de charger cette image.',
            mangaNotFound: 'Manga introuvable.',
            chapterNotFound: 'Chapitre introuvable.',
            genericError: 'Une erreur inattendue s\'est produite.'
        },
        success: {
            mangaLoaded: 'Manga chargé avec succès.',
            settingsSaved: 'Paramètres sauvegardés.'
        },
        info: {
            noMangas: 'Aucun manga trouvé.',
            loading: 'Chargement...',
            offline: 'Mode hors ligne activé.'
        }
    },

    // Keyboard shortcuts
    shortcuts: {
        'Escape': 'closeMenu',
        'ArrowLeft': 'previousChapter',
        'ArrowRight': 'nextChapter',
        'Space': 'togglePlayPause',
        'F': 'toggleFullscreen',
        'S': 'toggleSettings'
    },

    // Methods to get configuration values
    get: function(path, defaultValue = null) {
        const keys = path.split('.');
        let value = this;

        for (const key of keys) {
            if (value && typeof value === 'object' && key in value) {
                value = value[key];
            } else {
                return defaultValue;
            }
        }

        return value;
    },

    // Methods to set configuration values
    set: function(path, value) {
        const keys = path.split('.');
        const lastKey = keys.pop();
        let target = this;

        for (const key of keys) {
            if (!target[key] || typeof target[key] !== 'object') {
                target[key] = {};
            }
            target = target[key];
        }

        target[lastKey] = value;
    },

    // Check if a feature is enabled
    isFeatureEnabled: function(feature) {
        return this.get(`features.${feature}`, false);
    },

    // Get UI breakpoint for current screen size
    getCurrentBreakpoint: function() {
        const width = window.innerWidth;
        const breakpoints = this.get('ui.breakpoints', {});

        if (width <= breakpoints.mobile) return 'mobile';
        if (width <= breakpoints.tablet) return 'tablet';
        return 'desktop';
    },

    // Get animation duration
    getAnimationDuration: function(type = 'normal') {
        return this.get(`ui.animations.${type}`, 300);
    },

    // Get placeholder size for image type
    getPlaceholderSize: function(type) {
        return this.get(`ui.images.placeholderSizes.${type}`, { width: 200, height: 280 });
    },

    // Get error message
    getErrorMessage: function(key) {
        return this.get(`messages.errors.${key}`, 'Erreur inconnue');
    },

    // Get success message
    getSuccessMessage: function(key) {
        return this.get(`messages.success.${key}`, 'Opération réussie');
    },

    // Get info message
    getInfoMessage: function(key) {
        return this.get(`messages.info.${key}`, 'Information');
    },

    // Load user settings from localStorage
    loadUserSettings: function() {
        try {
            const settings = JSON.parse(localStorage.getItem(this.storage.settings) || '{}');
            return { ...this.defaults, ...settings };
        } catch (error) {
            console.warn('Failed to load user settings:', error);
            return this.defaults;
        }
    },

    // Save user settings to localStorage
    saveUserSettings: function(settings) {
        try {
            localStorage.setItem(this.storage.settings, JSON.stringify(settings));
            return true;
        } catch (error) {
            console.warn('Failed to save user settings:', error);
            return false;
        }
    },

    // Get API endpoint URL
    getApiUrl: function(endpoint, params = {}) {
        let url = this.get(`api.endpoints.${endpoint}`, '');

        // Replace parameters in URL
        Object.keys(params).forEach(key => {
            url = url.replace(`{${key}}`, params[key]);
        });

        return this.api.baseUrl + url;
    }
};

// Export for use in other modules
window.AppConfig = AppConfig;
