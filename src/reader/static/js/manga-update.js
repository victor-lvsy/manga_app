/**
 * Manga Update Module
 * Handles force update functionality with loading indicator
 */

class MangaUpdate {
    constructor() {
        this.isUpdating = false;
        this.pollingInterval = null;
        this.init();
    }

    init() {
        // Find all force update buttons
        const updateButtons = document.querySelectorAll('[data-force-update]');
        updateButtons.forEach(button => {
            button.addEventListener('click', (e) => this.handleUpdateClick(e, button));
        });

        // Also handle form submissions for backward compatibility
        const updateForms = document.querySelectorAll('form[action*="force_update"]');
        updateForms.forEach(form => {
            form.addEventListener('submit', (e) => this.handleFormSubmit(e, form));
        });

        // Check if update is pending and start polling
        this.checkPendingStatus();
    }

    checkPendingStatus() {
        // Check if any button has the 'updating' class (indicating pending status)
        const updateButtons = document.querySelectorAll('[data-force-update]');
        const pendingButton = Array.from(updateButtons).find(btn => btn.classList.contains('updating'));

        if (pendingButton) {
            const mangaId = pendingButton.dataset.mangaId || this.extractMangaIdFromForm(pendingButton.closest('form'));
            if (mangaId) {
                this.startPolling(mangaId);
            }
        }
    }

    startPolling(mangaId) {
        // Poll every 3 seconds
        this.pollingInterval = setInterval(async () => {
            try {
                const response = await fetch(`/manga/${mangaId}/status`, {
                    method: 'GET',
                    headers: {
                        'Accept': 'application/json',
                        'X-Requested-With': 'XMLHttpRequest'
                    },
                    credentials: 'same-origin'
                });

                if (!response.ok) {
                    console.error('Failed to fetch manga status');
                    return;
                }

                const data = await response.json();

                // If status is no longer pending, stop polling and reload
                if (data.update_status !== 'pending') {
                    this.stopPolling();
                    // Reload page to show updated status and chapters
                    window.location.reload();
                }
            } catch (error) {
                console.error('Error checking manga status:', error);
                // Continue polling even on error
            }
        }, 3000);
    }

    stopPolling() {
        if (this.pollingInterval) {
            clearInterval(this.pollingInterval);
            this.pollingInterval = null;
        }
    }

    handleFormSubmit(e, form) {
        e.preventDefault();
        const button = form.querySelector('button[type="submit"]');
        if (button) {
            this.handleUpdateClick(e, button);
        }
    }

    async handleUpdateClick(e, button) {
        e.preventDefault();

        if (this.isUpdating) {
            return; // Prevent multiple simultaneous updates
        }

        // Get manga ID from button or form
        const form = button.closest('form');
        const mangaId = button.dataset.mangaId || this.extractMangaIdFromForm(form);

        if (!mangaId) {
            console.error('Manga ID not found');
            return;
        }

        this.isUpdating = true;
        this.showLoading(button);
        this.disableButton(button);

        try {
            const response = await fetch(`/manga/${mangaId}/force_update`, {
                method: 'POST',
                headers: {
                    'Accept': 'application/json',
                    'X-Requested-With': 'XMLHttpRequest',
                    'Content-Type': 'application/json'
                },
                credentials: 'same-origin'
            });

            const data = await response.json();

            if (data.success) {
                // Update is now asynchronous, so start polling for status
                this.startPolling(mangaId);
            } else {
                this.showError(data.message);
                this.hideLoading(button);
                this.enableButton(button);
            }
        } catch (error) {
            console.error('Error updating manga:', error);
            this.showError('Erreur lors de la mise à jour. Veuillez réessayer.');
            this.hideLoading(button);
            this.enableButton(button);
        } finally {
            this.isUpdating = false;
        }
    }

    extractMangaIdFromForm(form) {
        if (!form) return null;
        const action = form.getAttribute('action');
        const match = action.match(/\/manga\/(\d+)\/force_update/);
        return match ? match[1] : null;
    }

    showLoading(button) {
        const originalText = button.innerHTML;
        button.dataset.originalText = originalText;

        // Create loading indicator
        const loadingHtml = `
            <span class="loading-spinner"></span>
            <span class="loading-text">Mise à jour...</span>
        `;
        button.innerHTML = loadingHtml;
        button.classList.add('updating');
    }

    hideLoading(button) {
        const originalText = button.dataset.originalText || '🔄 Force Update';
        button.innerHTML = originalText;
        button.classList.remove('updating');
    }

    disableButton(button) {
        button.disabled = true;
        button.classList.add('disabled');
    }

    enableButton(button) {
        button.disabled = false;
        button.classList.remove('disabled');
    }


    showError(message) {
        // Remove existing feedback
        this.removeExistingFeedback();

        // Create error message
        const feedback = document.createElement('div');
        feedback.className = 'alert alert-error update-feedback';
        feedback.innerHTML = `<strong>✗ ${message}</strong>`;

        // Insert at the top of container
        const container = document.querySelector('.container');
        if (container) {
            container.insertBefore(feedback, container.firstChild);
        }
    }

    removeExistingFeedback() {
        const existingFeedback = document.querySelector('.update-feedback');
        if (existingFeedback) {
            existingFeedback.remove();
        }
    }
}

// Initialize when DOM is ready
let mangaUpdateInstance = null;
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        mangaUpdateInstance = new MangaUpdate();
        window.mangaUpdate = mangaUpdateInstance;
    });
} else {
    mangaUpdateInstance = new MangaUpdate();
    window.mangaUpdate = mangaUpdateInstance;
}

// Clean up polling when page is unloaded
window.addEventListener('beforeunload', () => {
    if (mangaUpdateInstance) {
        mangaUpdateInstance.stopPolling();
    }
});

// Export for use in other modules
window.MangaUpdate = MangaUpdate;

