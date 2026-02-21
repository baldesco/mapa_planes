/**
 * search.js
 * Manages search functionality, results list, and map filtering.
 */
import apiClient from "../apiClient.js";
import mapHandler from "../mapHandler.js";

const search = {
    elements: {
        input: null,
        clearBtn: null,
        toggleFiltersBtn: null,
        filterForm: null,
        resultsPanel: null,
        resultsList: null,
        closeResultsBtn: null,
        mapOnlyToggle: null,
        hiddenQ: null,
        submitBtn: null,
        totalClearBtn: null,
        sortSelect: null,
        panelClearBtn: null
    },
    
    currentResults: [],
    originalOrderResults: [], // Store original relevance order
    searchTimeout: null,

    init() {
        console.log("Search module: Initializing...");
        this.cacheDOMElements();
        if (!this.elements.input) {
            console.warn("Search module: #search-input not found, skipping initialization.");
            return;
        }
        this.setupEventListeners();
        // Run initial search if q is present (e.g. from page reload)
        if (this.elements.input.value.trim()) {
            console.log("Search module: Initial search for query:", this.elements.input.value);
            this.handleSearch();
        }
    },

    cacheDOMElements() {
        this.elements.input = document.getElementById('search-input');
        this.elements.clearBtn = document.getElementById('clear-search-btn');
        this.elements.toggleFiltersBtn = document.getElementById('toggle-search-filters-btn');
        this.elements.filterForm = document.getElementById('filter-form');
        this.elements.resultsPanel = document.getElementById('search-results-panel');
        this.elements.resultsList = document.getElementById('search-results-list');
        this.elements.closeResultsBtn = document.getElementById('close-search-results-btn');
        this.elements.mapOnlyToggle = document.getElementById('search-only-map-toggle');
        this.elements.hiddenQ = document.getElementById('filter-q-hidden');
        this.elements.submitBtn = document.getElementById('search-submit-btn');
        this.elements.totalClearBtn = document.getElementById('clear-all-filters-btn');
        this.elements.sortSelect = document.getElementById('search-results-sort');
        this.elements.panelClearBtn = document.getElementById('panel-clear-search-btn');
    },

    setupEventListeners() {
        if (!this.elements.input) return;

        this.elements.input.addEventListener('input', () => {
            clearTimeout(this.searchTimeout);
            this.searchTimeout = setTimeout(() => this.handleSearch(), 500);
            this.updateClearButton();
        });

        this.elements.input.addEventListener('keydown', (e) => {
            if (e.key === 'Enter') {
                console.log("Search module: Enter key pressed");
                e.preventDefault();
                clearTimeout(this.searchTimeout);
                this.handleSearch();
            }
        });

        if (this.elements.submitBtn) {
            this.elements.submitBtn.addEventListener('click', (e) => {
                console.log("Search module: Lens button clicked");
                e.preventDefault();
                clearTimeout(this.searchTimeout);
                this.handleSearch();
            });
        }

        if (this.elements.totalClearBtn) {
            this.elements.totalClearBtn.addEventListener('click', (e) => {
                window.location.href = '/';
            });
        }

        this.elements.clearBtn.addEventListener('click', () => {
            this.elements.input.value = '';
            this.updateClearButton();
            this.handleSearch();
            this.elements.input.focus();
        });

        this.elements.toggleFiltersBtn.addEventListener('click', () => {
            const isHidden = this.elements.filterForm.style.display === 'none';
            this.elements.filterForm.style.display = isHidden ? 'block' : 'none';
            this.elements.toggleFiltersBtn.classList.toggle('active', isHidden);
        });

        this.elements.closeResultsBtn.addEventListener('click', () => {
            this.elements.resultsPanel.style.display = 'none';
        });

        if (this.elements.mapOnlyToggle) {
            this.elements.mapOnlyToggle.addEventListener('change', () => {
                this.applyMapFiltering();
            });
        }

        if (this.elements.sortSelect) {
            this.elements.sortSelect.addEventListener('change', () => {
                this.renderResults();
            });
        }

        if (this.elements.panelClearBtn) {
            this.elements.panelClearBtn.addEventListener('click', () => {
                this.clearAll();
            });
        }
        
        this.updateClearButton();
    },

    clearAll() {
        console.log("Search module: Clearing all filters...");
        if (this.elements.input) this.elements.input.value = '';
        if (this.elements.filterForm) this.elements.filterForm.reset();
        if (this.elements.hiddenQ) this.elements.hiddenQ.value = '';
        
        // Clear detailed filter visuals (tags) if tagInput is present
        // (Assuming window.tagInput or similar exists or we just reload)
        
        this.currentResults = [];
        this.originalOrderResults = [];
        this.updateClearButton();
        this.applyMapFiltering();
        if (this.elements.resultsPanel) this.elements.resultsPanel.style.display = 'none';
        
        // Also trigger the "Clear All" logic from the filters too if needed, 
        // but simplest is just window.location.href = '/' to be sure everything is clean
        window.location.href = '/';
    },

    updateClearButton() {
        if (this.elements.clearBtn) {
            this.elements.clearBtn.style.display = this.elements.input.value ? 'block' : 'none';
        }
    },

    async handleSearch() {
        if (!this.elements.input) return;
        const query = this.elements.input.value.trim();
        console.log("Search module: handleSearch called with query:", query);
        
        // Update hidden field for the filter form
        if (this.elements.hiddenQ) {
            this.elements.hiddenQ.value = query;
        }

        if (!query) {
            if (this.elements.resultsPanel) this.elements.resultsPanel.style.display = 'none';
            this.currentResults = [];
            this.applyMapFiltering();
            return;
        }

        // Show loading state
        if (this.elements.resultsPanel) {
            this.elements.resultsPanel.style.display = window.innerWidth > 768 ? 'flex' : 'block';
            this.elements.resultsList.innerHTML = '<div class="search-result-item">Loading...</div>';
        }

        try {
            // Get current filters and sanitize (avoid 422 errors)
            const formData = new FormData(this.elements.filterForm);
            const params = new URLSearchParams();
            params.set('q', query);
            
            // Only add filters if they have values
            for (const [key, value] of formData.entries()) {
                if (value && key !== 'q') {
                    params.append(key, value);
                }
            }
            
            const apiUrl = `/api/v1/places/?${params.toString()}`;
            console.log("Search module: Fetching results from:", apiUrl);

            const response = await apiClient.get(apiUrl);
            if (response.ok) {
                this.currentResults = await response.json();
                this.originalOrderResults = [...this.currentResults]; // Back up relevance order
                console.log(`Search module: Found ${this.currentResults.length} results`);
                this.renderResults();
                this.applyMapFiltering();
            } else {
                console.error("Search module: API returned error", response.status);
                this.elements.resultsList.innerHTML = `<div class="search-result-item error">Error loading results (${response.status})</div>`;
            }
        } catch (error) {
            console.error("Search failed:", error);
            this.elements.resultsList.innerHTML = '<div class="search-result-item error">Search failed. Check console.</div>';
        }
    },

    renderResults() {
        const list = this.elements.resultsList;
        if (!list) return;
        list.innerHTML = '';
        
        const sortMode = this.elements.sortSelect?.value || 'relevance';
        let resultsToSort = [...this.currentResults];

        if (sortMode === 'name') {
            resultsToSort.sort((a, b) => a.name.localeCompare(b.name));
        } else if (sortMode === 'rating') {
            resultsToSort.sort((a, b) => {
                const getAvg = (p) => {
                    const ratedVisits = p.visits?.filter(v => v.rating) || [];
                    if (ratedVisits.length === 0) return -1;
                    return ratedVisits.reduce((acc, v) => acc + v.rating, 0) / ratedVisits.length;
                };
                return getAvg(b) - getAvg(a);
            });
        } else if (sortMode === 'relevance') {
            resultsToSort = [...this.originalOrderResults];
        }
        
        if (resultsToSort.length === 0) {
            list.innerHTML = '<div class="search-result-item">No results found</div>';
        } else {
            resultsToSort.forEach(place => {
                const item = document.createElement('div');
                item.className = 'search-result-item';
                
                // Calculate average rating for display
                const ratedVisits = place.visits?.filter(v => v.rating) || [];
                const avgRating = ratedVisits.length > 0 
                    ? ratedVisits.reduce((acc, v) => acc + v.rating, 0) / ratedVisits.length 
                    : null;
                
                let starsHtml = '';
                if (avgRating) {
                    const fullStars = Math.floor(avgRating);
                    starsHtml = '<div class="search-result-rating">';
                    for (let i = 0; i < 5; i++) {
                        starsHtml += `<i class="${i < fullStars ? 'fas' : 'far'} fa-star"></i>`;
                    }
                    starsHtml += ` <span>(${avgRating.toFixed(1)})</span></div>`;
                }

                item.innerHTML = `
                    <span class="search-result-name">${place.name}</span>
                    <span class="search-result-meta">${place.category} • ${place.city || place.country || ''}</span>
                    ${starsHtml}
                    ${place.description ? `<p class="search-result-desc">${place.description}</p>` : ''}
                `;
                item.addEventListener('click', () => {
                    mapHandler.flyTo(place.latitude, place.longitude);
                    const marker = mapHandler.getMarkerById(place.id);
                    if (marker) marker.openPopup();
                });
                list.appendChild(item);
            });
        }
        
        if (this.elements.resultsPanel) {
            if (window.innerWidth > 768) {
                this.elements.resultsPanel.style.display = 'flex';
            } else {
                this.elements.resultsPanel.style.display = 'block';
            }
        }
    },

    applyMapFiltering() {
        const onlyShowResults = this.elements.mapOnlyToggle?.checked;
        const query = this.elements.input.value.trim();
        
        console.log("Search module: Applying map filtering. OnlyShowResults:", onlyShowResults);

        if (onlyShowResults && query) {
            // Fix ID Type Mismatch: ensure we compare same types (strings vs strings)
            const resultIds = new Set(this.currentResults.map(p => String(p.id)));
            console.log("Search module: Filtering map to IDs:", [...resultIds]);
            
            mapHandler.filterMarkers(id => {
                const isMatch = resultIds.has(String(id));
                return isMatch;
            });
        } else {
            console.log("Search module: Showing all markers");
            mapHandler.filterMarkers(() => true);
        }
    }
};

export default search;
