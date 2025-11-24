class AddMangaPage {
    constructor() {
        this.form = document.querySelector('.form-card');
        if (!this.form) return;

        this.nameInput = this.form.querySelector('input[name="name"]');
        this.urlInput = this.form.querySelector('input[name="url"]');
        this.scanlationSelect = this.form.querySelector('select[name="scanlation_group"]');
        this.tagsInput = this.form.querySelector('input[name="tags"]');
        this.folderPreview = document.querySelector('[data-folder-preview]');
        this.scanlationHint = document.querySelector('[data-scanlation-hint]');
        this.urlStatus = document.querySelector('[data-url-status]');
        this.tagStatus = document.querySelector('[data-tag-status]');
        this.tagContainer = document.querySelector('.tag-suggestions');
        this.availableTags = this.getAvailableTags();
        this.selectedTags = new Set(this.getInitialTags());

        this.init();
    }

    init() {
        this.updateFolderPreview();
        this.updateTagStatus();
        this.reflectSelectedTags();
        this.bindEvents();
    }

    bindEvents() {
        this.nameInput?.addEventListener('input', () => this.updateFolderPreview());
        this.urlInput?.addEventListener('input', Utils.debounce(() => this.handleUrlInput(), 500));
        this.scanlationSelect?.addEventListener('change', Utils.debounce(() => this.validateUrl(), 300));
        this.tagsInput?.addEventListener('keydown', (event) => this.handleTagInputKey(event));
        this.tagsInput?.addEventListener('blur', () => this.commitFreeformTags());

        if (this.tagContainer) {
            this.tagContainer.addEventListener('click', (event) => {
                const chip = event.target.closest('.tag-chip');
                if (!chip) return;
                this.toggleTag(chip.dataset.tag);
            });
        }

        this.form.addEventListener('submit', () => {
            this.commitFreeformTags();
            this.syncTagsInput();
        });
    }

    getAvailableTags() {
        if (!this.tagContainer?.dataset.tags) return [];
        try {
            const parsed = JSON.parse(this.tagContainer.dataset.tags);
            return Array.isArray(parsed) ? parsed : [];
        } catch (error) {
            console.warn('Invalid tags payload', error);
            return [];
        }
    }

    getInitialTags() {
        if (!this.tagsInput?.value) return [];
        return this.tagsInput.value
            .split(',')
            .map(tag => tag.trim())
            .filter(Boolean);
    }

    slugifyName(name) {
        return name
            .normalize('NFD')
            .replace(/[\u0300-\u036f]/g, '')
            .replace(/[^a-zA-Z0-9]+/g, '_')
            .replace(/_+/g, '_')
            .replace(/^_|_$/g, '')
            .toLowerCase() || 'nouveau_manga';
    }

    updateFolderPreview() {
        if (!this.folderPreview || !this.nameInput) return;
        const slug = this.slugifyName(this.nameInput.value.trim());
        this.folderPreview.textContent = `${slug}`;
    }

    handleUrlInput() {
        if (!this.urlInput) return;
        const url = this.urlInput.value.trim();

        if (!url) {
            this.setUrlStatus('URL requise.', 'neutral');
            this.urlInput.classList.remove('field-error', 'field-valid');
            return;
        }

        try {
            const parsed = new URL(url);
            this.setUrlStatus(`Domaine détecté : ${parsed.hostname}`, 'neutral');
            this.autodetectScanlation(parsed.hostname);
            this.validateUrl();
        } catch (error) {
            this.setUrlStatus("URL invalide, vérifiez le format.", 'error');
            this.urlInput.classList.add('field-error');
            this.urlInput.classList.remove('field-valid');
        }
    }

    async validateUrl() {
        if (!this.urlInput || !this.scanlationSelect) return;
        const url = this.urlInput.value.trim();
        const scanlationGroup = this.scanlationSelect.value;

        if (!url || !scanlationGroup) {
            this.setUrlStatus('URL et scanlation requises pour la validation.', 'neutral');
            return;
        }

        // Basic URL format check
        try {
            new URL(url);
        } catch (error) {
            this.setUrlStatus("URL invalide, vérifiez le format.", 'error');
            this.urlInput.classList.add('field-error');
            this.urlInput.classList.remove('field-valid');
            return;
        }

        this.setUrlStatus('Vérification en cours...', 'neutral');
        this.urlInput.classList.remove('field-error', 'field-valid');

        try {
            const response = await fetch(`/add_manga/validate?url=${encodeURIComponent(url)}&scanlation_group=${encodeURIComponent(scanlationGroup)}`);
            const data = await response.json();

            if (data.valid) {
                const chapterText = data.chapter_count === 1 ? 'chapitre' : 'chapitres';
                this.setUrlStatus(`✓ ${data.chapter_count} ${chapterText} trouvé(s)`, 'success');
                this.urlInput.classList.add('field-valid');
                this.urlInput.classList.remove('field-error');
            } else {
                this.setUrlStatus(`✗ ${data.error || 'URL invalide'}`, 'error');
                this.urlInput.classList.add('field-error');
                this.urlInput.classList.remove('field-valid');
            }
        } catch (error) {
            console.error('Validation error:', error);
            this.setUrlStatus('Erreur lors de la validation.', 'error');
            this.urlInput.classList.add('field-error');
            this.urlInput.classList.remove('field-valid');
        }
    }

    setUrlStatus(message, state = 'neutral') {
        if (!this.urlStatus) return;
        this.urlStatus.textContent = message;
        this.urlStatus.dataset.state = state;
    }

    autodetectScanlation(hostname) {
        if (!this.scanlationSelect || !this.scanlationHint) return;

        const mapping = [
            { keyword: 'asura', value: 'asura_scans', label: 'Asura Scans' },
            { keyword: 'mangafire', value: 'mangafire_to', label: 'MangaFire' }
        ];

        const match = mapping.find(item => hostname.includes(item.keyword));
        if (match) {
            this.scanlationSelect.value = match.value;
            this.scanlationHint.textContent = match.label;
        } else {
            this.scanlationHint.textContent = 'Non reconnue';
        }
    }

    handleTagInputKey(event) {
        if (event.key === 'Enter' || event.key === ',') {
            event.preventDefault();
            this.commitFreeformTags();
        }
        if (event.key === 'Backspace' && !event.target.value && this.selectedTags.size) {
            // Remove last tag
            const last = Array.from(this.selectedTags).pop();
            this.selectedTags.delete(last);
            this.syncTagsInput();
            this.reflectSelectedTags();
            this.updateTagStatus();
        }
    }

    commitFreeformTags() {
        if (!this.tagsInput) return;
        const value = this.tagsInput.value.trim();
        if (!value) return;

        const chunked = value.split(',').map(tag => tag.trim()).filter(Boolean);
        chunked.forEach(tag => this.addTag(tag));
        this.tagsInput.value = '';
    }

    addTag(tag) {
        if (!tag) return;
        if (this.availableTags.length && !this.availableTags.includes(tag)) {
            Utils.showNotification(`Tag "${tag}" inconnu.`, 'warning', 2000);
            return;
        }
        this.selectedTags.add(tag);
        this.syncTagsInput();
        this.reflectSelectedTags();
        this.updateTagStatus();
    }

    toggleTag(tag) {
        if (!tag) return;
        if (this.selectedTags.has(tag)) {
            this.selectedTags.delete(tag);
        } else {
            this.selectedTags.add(tag);
        }

        this.syncTagsInput();
        this.reflectSelectedTags();
        this.updateTagStatus();
    }

    syncTagsInput() {
        if (!this.tagsInput) return;
        this.tagsInput.value = Array.from(this.selectedTags).join(', ');
    }

    reflectSelectedTags() {
        if (!this.tagContainer) return;
        const chips = this.tagContainer.querySelectorAll('.tag-chip');
        chips.forEach(chip => {
            chip.classList.toggle('is-active', this.selectedTags.has(chip.dataset.tag));
        });
    }

    updateTagStatus() {
        if (!this.tagStatus) return;
        if (!this.selectedTags.size) {
            this.tagStatus.textContent = 'Aucun tag sélectionné.';
            return;
        }
        this.tagStatus.textContent = `${this.selectedTags.size} tag(s) sélectionné(s).`;
    }
}

document.addEventListener('DOMContentLoaded', () => {
    window.addMangaPage = new AddMangaPage();
});

