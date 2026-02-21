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
        hiddenQ: null
    },
    
    currentResults: [],
    searchTimeout: null,

    init() {
        this.cacheDOMElements();
        this.setupEventListeners();
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
    },

    setupEventListeners() {
        if (!this.elements.input) return;

        this.elements.input.addEventListener('input', () => {
            clearTimeout(this.searchTimeout);
            this.searchTimeout = setTimeout(() => this.handleSearch(), 500);
            this.updateClearButton();
        });

        this.elements.input.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                clearTimeout(this.searchTimeout);
                this.handleSearch();
            }
        });

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
        
        this.updateClearButton();
    },

    updateClearButton() {
        if (this.elements.clearBtn) {
            this.elements.clearBtn.style.display = this.elements.input.value ? 'block' : 'none';
        }
    },

    async handleSearch() {
        const query = this.elements.input.value.trim();
        
        // Update hidden field for the filter form
        if (this.elements.hiddenQ) {
            this.elements.hiddenQ.value = query;
        }

        if (!query) {
            this.elements.resultsPanel.style.display = 'none';
            this.currentResults = [];
            this.applyMapFiltering();
            return;
        }

        try {
            // Get current filters
            const formData = new FormData(this.elements.filterForm);
            const params = new URLSearchParams(formData);
            params.set('q', query);
            
            const response = await apiClient.get(`/api/v1/places/?${params.toString()}`);
            if (response.ok) {
                this.currentResults = await response.json();
                this.renderResults();
                this.applyMapFiltering();
            }
        } catch (error) {
            console.error("Search failed:", error);
        }
    },

    renderResults() {
        const list = this.elements.resultsList;
        list.innerHTML = '';
        
        if (this.currentResults.length === 0) {
            list.innerHTML = '<div class="search-result-item">No results found</div>';
        } else {
            this.currentResults.forEach(place => {
                const item = document.createElement('div');
                item.className = 'search-result-item';
                item.innerHTML = `
                    <span class="search-result-name">${place.name}</span>
                    <span class="search-result-meta">${place.category} • ${place.city || place.country || ''}</span>
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
        
        this.elements.resultsPanel.style.display = 'flex';
    },

    applyMapFiltering() {
        const onlyShowResults = this.elements.mapOnlyToggle?.checked;
        const query = this.elements.input.value.trim();
        
        if (onlyShowResults && query) {
            const resultIds = new Set(this.currentResults.map(p => p.id));
            mapHandler.filterMarkers(id => resultIds.has(id));
        } else {
            // Show all markers (that match current category/status filters if any)
            // For now, reset to all
            mapHandler.filterMarkers(() => true);
        }
    }
};

export default search;
