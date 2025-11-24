/**
 * Navigation Module
 * Handles mobile navigation, hamburger menu, and navigation interactions
 */

class NavigationManager {
    constructor() {
        this.hamburger = null;
        this.navMenu = null;
        this.navLinks = null;
        this.isMenuOpen = false;

        this.init();
    }

    init() {
        // Wait for DOM to be ready
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', () => this.setupElements());
        } else {
            this.setupElements();
        }
    }

    setupElements() {
        this.hamburger = document.getElementById('hamburger');
        this.navMenu = document.getElementById('nav-menu');
        this.navLinks = document.querySelectorAll('.nav-link');

        this.bindEvents();
    }

    bindEvents() {
        // Only bind interactive menu behavior on mobile to avoid desktop animations
        const isMobile = () => window.innerWidth <= 768;

        if (this.hamburger && this.navMenu) {
            // Hamburger menu toggle (mobile only)
            this.hamburger.addEventListener('click', (e) => {
                if (!isMobile()) return;
                e.preventDefault();
                this.toggleMenu();
            });

            // Close menu when clicking on nav links (mobile only)
            this.navLinks.forEach(link => {
                link.addEventListener('click', () => {
                    if (!isMobile()) return;
                    this.closeMenu();
                });
            });

            // Close menu when clicking outside (mobile only)
            document.addEventListener('click', (e) => {
                if (!isMobile()) return;
                if (!this.hamburger.contains(e.target) && !this.navMenu.contains(e.target)) {
                    this.closeMenu();
                }
            });

            // Close menu on escape key (mobile only)
            document.addEventListener('keydown', (e) => {
                if (!isMobile()) return;
                if (e.key === 'Escape' && this.isMenuOpen) {
                    this.closeMenu();
                }
            });

            // Handle window resize: if leaving mobile, ensure menu is closed
            window.addEventListener('resize', () => {
                if (!isMobile() && this.isMenuOpen) {
                    this.closeMenu();
                }
            });
        }
    }

    toggleMenu() {
        if (this.isMenuOpen) {
            this.closeMenu();
        } else {
            this.openMenu();
        }
    }

    openMenu() {
        this.hamburger.classList.add('active');
        this.navMenu.classList.add('active');
        this.isMenuOpen = true;

        // Prevent body scroll when menu is open
        document.body.style.overflow = 'hidden';
    }

    closeMenu() {
        this.hamburger.classList.remove('active');
        this.navMenu.classList.remove('active');
        this.isMenuOpen = false;

        // Restore body scroll
        document.body.style.overflow = '';
    }

    // Public method to set active nav item
    setActiveNavItem(activePath) {
        this.navLinks.forEach(link => {
            link.classList.remove('active');
            if (link.getAttribute('href') === activePath) {
                link.classList.add('active');
            }
        });
    }
}

// Initialize navigation when script loads
const navigationManager = new NavigationManager();

// Export for use in other modules
window.NavigationManager = NavigationManager;
