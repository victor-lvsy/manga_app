document.addEventListener('DOMContentLoaded', function() {
    const listViewBtn = document.getElementById('list-view-btn');
    const gridViewBtn = document.getElementById('grid-view-btn');
    const listView = document.getElementById('manga-list-view');
    const gridView = document.getElementById('manga-grid-view');
    const showAllToggle = document.getElementById('show-all-toggle');
    const sortSelect = document.getElementById('sort-select');
    const typeFilter = document.getElementById('type-filter');
    const tagFilterToggle = document.getElementById('tag-filter-toggle');
    const tagFilterDropdown = document.getElementById('tag-filter-dropdown');
    const tagFilterText = document.getElementById('tag-filter-text');
    const tagFilterCount = document.getElementById('tag-filter-count');
    const tagCheckboxes = document.querySelectorAll('.tag-checkbox');
    const selectAllTagsBtn = document.getElementById('select-all-tags');
    const deselectAllTagsBtn = document.getElementById('deselect-all-tags');

    const savedView = localStorage.getItem('manga-view-preference') || 'list';
    const savedShowAll = localStorage.getItem('show-all-mangas') !== 'false';
    const savedSort = localStorage.getItem('manga-sort') || 'date-desc';
    const savedType = localStorage.getItem('manga-type-filter') || 'all';
    const savedTags = JSON.parse(localStorage.getItem('manga-tag-filters') || '[]');

    setView(savedView);
    if (showAllToggle) showAllToggle.checked = savedShowAll;
    if (sortSelect) sortSelect.value = savedSort;
    if (typeFilter) typeFilter.value = savedType;

    // Restore saved tag selections
    if (savedTags.length > 0 && tagCheckboxes.length > 0) {
        tagCheckboxes.forEach(function(checkbox) {
            const tagValue = checkbox.getAttribute('data-tag');
            if (savedTags.indexOf(tagValue) !== -1) {
                checkbox.checked = true;
            }
        });
    }

    updateTagFilterUI();
    applyFiltersAndSort();

    if (listViewBtn) {
        listViewBtn.addEventListener('click', function() {
            setView('list');
            localStorage.setItem('manga-view-preference', 'list');
        });
    }

    if (gridViewBtn) {
        gridViewBtn.addEventListener('click', function() {
            setView('grid');
            localStorage.setItem('manga-view-preference', 'grid');
        });
    }

    if (showAllToggle) {
        showAllToggle.addEventListener('change', function() {
            localStorage.setItem('show-all-mangas', this.checked);
            applyFiltersAndSort();
        });
    }

    if (sortSelect) {
        sortSelect.addEventListener('change', function() {
            localStorage.setItem('manga-sort', this.value);
            applyFiltersAndSort();
        });
    }

    if (typeFilter) {
        typeFilter.addEventListener('change', function() {
            localStorage.setItem('manga-type-filter', this.value);
            applyFiltersAndSort();
        });
    }

    // Tag filter toggle
    if (tagFilterToggle && tagFilterDropdown) {
        tagFilterToggle.addEventListener('click', function(e) {
            e.stopPropagation();
            const isVisible = tagFilterDropdown.style.display !== 'none';
            tagFilterDropdown.style.display = isVisible ? 'none' : 'block';
        });

        // Close dropdown when clicking outside
        document.addEventListener('click', function(e) {
            if (!tagFilterToggle.contains(e.target) && !tagFilterDropdown.contains(e.target)) {
                tagFilterDropdown.style.display = 'none';
            }
        });
    }

    // Tag checkbox changes
    tagCheckboxes.forEach(function(checkbox) {
        checkbox.addEventListener('change', function() {
            saveSelectedTags();
            updateTagFilterUI();
            applyFiltersAndSort();
        });
    });

    // Select all tags
    if (selectAllTagsBtn) {
        selectAllTagsBtn.addEventListener('click', function() {
            tagCheckboxes.forEach(function(checkbox) {
                checkbox.checked = true;
            });
            saveSelectedTags();
            updateTagFilterUI();
            applyFiltersAndSort();
        });
    }

    // Deselect all tags
    if (deselectAllTagsBtn) {
        deselectAllTagsBtn.addEventListener('click', function() {
            tagCheckboxes.forEach(function(checkbox) {
                checkbox.checked = false;
            });
            saveSelectedTags();
            updateTagFilterUI();
            applyFiltersAndSort();
        });
    }

    function setView(view) {
        if (!listView || !gridView || !listViewBtn || !gridViewBtn) return;

        if (view === 'list') {
            listView.style.display = 'block';
            gridView.style.display = 'none';
            listViewBtn.classList.add('active');
            gridViewBtn.classList.remove('active');
        } else {
            listView.style.display = 'none';
            gridView.style.display = 'grid';
            listViewBtn.classList.remove('active');
            gridViewBtn.classList.add('active');
        }
    }

    function getSelectedTags() {
        const selected = [];
        tagCheckboxes.forEach(function(checkbox) {
            if (checkbox.checked) {
                selected.push(checkbox.getAttribute('data-tag'));
            }
        });
        return selected;
    }

    function saveSelectedTags() {
        const selected = getSelectedTags();
        localStorage.setItem('manga-tag-filters', JSON.stringify(selected));
    }

    function updateTagFilterUI() {
        const selected = getSelectedTags();
        if (selected.length === 0) {
            tagFilterText.textContent = 'Sélectionner des tags';
            tagFilterCount.style.display = 'none';
        } else {
            tagFilterText.textContent = selected.length === 1 ? '1 tag sélectionné' : selected.length + ' tags sélectionnés';
            tagFilterCount.textContent = selected.length;
            tagFilterCount.style.display = 'inline';
        }
    }

    function applyFiltersAndSort() {
        const showAll = showAllToggle ? showAllToggle.checked : true;
        const sortBy = sortSelect ? sortSelect.value : 'date-desc';
        const typeFilterValue = typeFilter ? typeFilter.value : 'all';
        const selectedTags = getSelectedTags();

        const listItems = listView ? Array.from(listView.querySelectorAll('.manga-list-item')) : [];
        const gridItems = gridView ? Array.from(gridView.querySelectorAll('.manga-card')) : [];

        // Filter items
        const filteredListItems = listItems.filter(function(item) {
            return shouldShowItem(item, showAll, typeFilterValue, selectedTags);
        });

        const filteredGridItems = gridItems.filter(function(item) {
            return shouldShowItem(item, showAll, typeFilterValue, selectedTags);
        });

        // Sort items
        sortItems(filteredListItems, sortBy);
        sortItems(filteredGridItems, sortBy);

        // Hide all items first
        listItems.forEach(function(item) { item.style.display = 'none'; });
        gridItems.forEach(function(item) { item.style.display = 'none'; });

        // Show filtered and sorted items
        filteredListItems.forEach(function(item) { item.style.display = ''; });
        filteredGridItems.forEach(function(item) { item.style.display = ''; });

        // Reorder in DOM
        filteredListItems.forEach(function(item) {
            listView.appendChild(item);
        });
        filteredGridItems.forEach(function(item) {
            gridView.appendChild(item);
        });
    }

    function shouldShowItem(item, showAll, typeFilterValue, selectedTags) {
        // Filter by follow status
        const isFollowed = item.getAttribute('data-followed') === 'true';
        if (!showAll && !isFollowed) {
            return false;
        }

        // Filter by type
        if (typeFilterValue !== 'all') {
            const comicType = item.getAttribute('data-comic-type');
            if (comicType !== typeFilterValue) {
                return false;
            }
        }

        // Filter by tags (show if manga has ALL of the selected tags)
        if (selectedTags.length > 0) {
            const tags = item.getAttribute('data-tags') || '';
            const tagArray = tags.split(',').map(function(t) { return t.trim().toLowerCase(); });
            // Check if manga has ALL selected tags
            const hasAllTags = selectedTags.every(function(selectedTag) {
                return tagArray.indexOf(selectedTag.toLowerCase()) !== -1;
            });
            if (!hasAllTags) {
                return false;
            }
        }

        return true;
    }

    function sortItems(items, sortBy) {
        items.sort(function(a, b) {
            if (sortBy === 'name-asc') {
                const nameA = (a.getAttribute('data-name') || '').toLowerCase();
                const nameB = (b.getAttribute('data-name') || '').toLowerCase();
                return nameA.localeCompare(nameB);
            } else if (sortBy === 'name-desc') {
                const nameA = (a.getAttribute('data-name') || '').toLowerCase();
                const nameB = (b.getAttribute('data-name') || '').toLowerCase();
                return nameB.localeCompare(nameA);
            } else if (sortBy === 'date-asc') {
                const timestampA = parseInt(a.getAttribute('data-timestamp') || '0', 10);
                const timestampB = parseInt(b.getAttribute('data-timestamp') || '0', 10);
                return timestampA - timestampB;
            } else { // date-desc (default)
                const timestampA = parseInt(a.getAttribute('data-timestamp') || '0', 10);
                const timestampB = parseInt(b.getAttribute('data-timestamp') || '0', 10);
                return timestampB - timestampA;
            }
        });
    }
});


