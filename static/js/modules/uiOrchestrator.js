/**
 * uiOrchestrator.js
 * Central manager for application state and UI coordination.
 * Handles the logic for SPA-lite updates, filtering, and component synchronization.
 */

import addPlaceForm from "./forms/addPlaceForm.js";
import editPlaceForm from "./forms/editPlaceForm.js";
import reviewForm from "./forms/reviewForm.js";
import visitForm from "./forms/visitForm.js";
import icsCustomizeForm from "./forms/icsCustomizeForm.js";
import modals from "./components/modals.js";
import pinningUI from "./components/pinningUI.js";
import mapHandler from "./mapHandler.js";
import sidebar from "./components/sidebar.js";
import tagInput from "./components/tagInput.js";
import { setStatusMessage } from "./components/statusMessages.js";
import apiClient from "./apiClient.js";

const uiOrchestrator = {
  state: {
    allPlaces: [],
    filteredPlaces: [],
    allUserTags: [],
    filters: {
      search: "",
      category: "",
      status: "",
      tags: [],
    },
    activePlaceId: null,
  },

  elements: {
    globalSearch: null,
    toggleFiltersBtn: null,
    filterPanel: null,
    categorySelect: null,
    statusSelect: null,
    tagFilterInput: null,
    clearFiltersBtn: null,
    toggleAddPlaceBtn: null,
    // Overlays
    addPlaceWrapper: null,
    editPlaceSection: null,
    visitReviewImageSection: null,
    seeVisitReviewSection: null,
    planVisitSection: null,
    visitsListModal: null,
    icsCustomizeModal: null,
  },

  init() {
    this.cacheDOMElements();
    this.loadInitialData();

    // Initialize Map
    const mapDataElement = document.getElementById("map-data");
    const mapData = mapDataElement
      ? JSON.parse(mapDataElement.textContent || "{}")
      : {};
    this.state.allPlaces = mapData.places || [];
    this.state.filteredPlaces = [...this.state.allPlaces];

    const isMapReady = mapHandler.initMainMap("map", mapData);

    // Initialize Components
    sidebar.init(this.handlePlaceSelection.bind(this));

    addPlaceForm.init(
      isMapReady,
      this.showAddPlaceForm.bind(this),
      this.hideAddPlaceForm.bind(this),
    );

    editPlaceForm.init(
      isMapReady,
      this.showEditPlaceForm.bind(this),
      this.hideEditPlaceForm.bind(this),
    );

    reviewForm.init(this.hideOverlays.bind(this), (updatedVisit) =>
      this.handleVisitUpdate(updatedVisit),
    );

    visitForm.init(this.hideOverlays.bind(this), (newVisit) =>
      this.handleVisitUpdate(newVisit),
    );

    icsCustomizeForm.init(this.hideOverlays.bind(this));
    modals.init(this.showVisitReviewForm.bind(this));
    pinningUI.init(isMapReady);

    this.setupTagFilters();
    this.setupEventListeners();

    // Initial Render
    this.refreshUI();

    // Global Bindings for Popups
    window.showEditPlaceForm = this.showEditPlaceForm.bind(this);
    window.showPlanVisitForm = this.showPlanVisitForm.bind(this);
    window.showVisitsListModal = this.showVisitsListModal.bind(this);
    window.showSeeVisitReviewModal = modals.showSeeReviewModal.bind(modals);
    window.showVisitReviewForm = this.showVisitReviewForm.bind(this);
    window.showIcsCustomizeModal = this.showIcsCustomizeModal.bind(this);
    window.showImageOverlay = modals.showImageOverlay.bind(modals);
  },

  cacheDOMElements() {
    this.elements.globalSearch = document.getElementById("global-search");
    this.elements.toggleFiltersBtn =
      document.getElementById("toggle-filters-btn");
    this.elements.filterPanel = document.getElementById("filter-panel");
    this.elements.categorySelect = document.getElementById("category");
    this.elements.statusSelect = document.getElementById("status");
    this.elements.tagFilterInput = document.getElementById("tag-filter-input");
    this.elements.clearFiltersBtn =
      document.getElementById("clear-filters-btn");
    this.elements.toggleAddPlaceBtn = document.getElementById(
      "toggle-add-place-form-btn",
    );

    this.elements.addPlaceWrapper = document.getElementById(
      "add-place-wrapper-section",
    );
    this.elements.editPlaceSection =
      document.getElementById("edit-place-section");
    this.elements.visitReviewImageSection = document.getElementById(
      "visit-review-image-section",
    );
    this.elements.seeVisitReviewSection = document.getElementById(
      "see-visit-review-section",
    );
    this.elements.planVisitSection =
      document.getElementById("plan-visit-section");
    this.elements.visitsListModal =
      document.getElementById("visits-list-modal");
    this.elements.icsCustomizeModal = document.getElementById(
      "ics-customize-modal",
    );
  },

  loadInitialData() {
    const tagsDataElement = document.getElementById("user-tags-data");
    if (tagsDataElement) {
      const tagsData = JSON.parse(tagsDataElement.textContent || "[]");
      this.state.allUserTags = tagsData.map((tag) => tag.name);
    }
  },

  setupTagFilters() {
    if (this.elements.tagFilterInput) {
      const tagify = tagInput.init("tag-filter-input", this.state.allUserTags, {
        placeholder: "Filter by tags...",
      });
      if (tagify) {
        tagify.on("change", () => {
          this.state.filters.tags = tagify.value.map((t) =>
            t.value.toLowerCase(),
          );
          this.applyFilters();
        });
      }
    }
  },

  setupEventListeners() {
    this.elements.globalSearch?.addEventListener("input", (e) => {
      this.state.filters.search = e.target.value.toLowerCase();
      this.applyFilters();
    });

    this.elements.categorySelect?.addEventListener("change", (e) => {
      this.state.filters.category = e.target.value;
      this.applyFilters();
    });

    this.elements.statusSelect?.addEventListener("change", (e) => {
      this.state.filters.status = e.target.value;
      this.applyFilters();
    });

    this.elements.clearFiltersBtn?.addEventListener("click", () => {
      this.elements.globalSearch.value = "";
      this.elements.categorySelect.value = "";
      this.elements.statusSelect.value = "";
      const tagify = tagInput.tagifyInstances["tag-filter-input"];
      if (tagify) tagify.removeAllTags();

      this.state.filters = { search: "", category: "", status: "", tags: [] };
      this.applyFilters();
    });

    this.elements.toggleFiltersBtn?.addEventListener("click", () => {
      const isHidden = this.elements.filterPanel.style.display === "none";
      this.elements.filterPanel.style.display = isHidden ? "block" : "none";
    });

    this.elements.toggleAddPlaceBtn?.addEventListener("click", () =>
      this.showAddPlaceForm(),
    );
  },

  applyFilters() {
    const { search, category, status, tags } = this.state.filters;

    this.state.filteredPlaces = this.state.allPlaces.filter((place) => {
      const matchesSearch =
        !search ||
        place.name.toLowerCase().includes(search) ||
        (place.address && place.address.toLowerCase().includes(search));

      const matchesCategory = !category || place.category === category;
      const matchesStatus = !status || place.status === status;

      const matchesTags =
        tags.length === 0 ||
        tags.every((t) =>
          place.tags.some((pt) => (pt.name || pt).toLowerCase() === t),
        );

      return matchesSearch && matchesCategory && matchesStatus && matchesTags;
    });

    this.refreshUI();
  },

  refreshUI() {
    sidebar.render(this.state.filteredPlaces);
    mapHandler.renderMarkers(this.state.filteredPlaces);
    if (this.state.activePlaceId) {
      sidebar.setActiveCard(this.state.activePlaceId);
    }
  },

  handlePlaceSelection(placeId) {
    this.state.activePlaceId = placeId;
    const place = this.state.allPlaces.find((p) => p.id === placeId);
    if (place) {
      mapHandler.flyTo(place.latitude, place.longitude);
    }
  },

  /**
   * SPA-lite update handler. Updates local state and refreshes UI
   * without a full page reload.
   */
  async handlePlaceUpdate(updatedPlace) {
    const index = this.state.allPlaces.findIndex(
      (p) => p.id === updatedPlace.id,
    );
    if (index !== -1) {
      this.state.allPlaces[index] = updatedPlace;
    } else {
      this.state.allPlaces.unshift(updatedPlace);
    }
    this.applyFilters();
    this.hideOverlays();
  },

  async handleVisitUpdate(updatedVisit) {
    const placeId = updatedVisit.place_id;
    try {
      const response = await apiClient.get(`/api/v1/places/${placeId}`);
      if (response.ok) {
        const updatedPlace = await response.json();
        this.handlePlaceUpdate(updatedPlace);
      }
    } catch (e) {
      console.error("Failed to re-sync place after visit update", e);
    }
  },

  hideOverlays() {
    const overlays = [
      this.elements.addPlaceWrapper,
      this.elements.editPlaceSection,
      this.elements.visitReviewImageSection,
      this.elements.seeVisitReviewSection,
      this.elements.planVisitSection,
      this.elements.visitsListModal,
      this.elements.icsCustomizeModal,
    ];
    overlays.forEach((el) => {
      if (el) el.style.display = "none";
    });
    pinningUI.deactivatePinning();
  },

  showAddPlaceForm() {
    this.hideOverlays();
    addPlaceForm.resetForm();
    this.elements.addPlaceWrapper.style.display = "block";
  },

  hideAddPlaceForm() {
    this.elements.addPlaceWrapper.style.display = "none";
    pinningUI.deactivatePinning();
  },

  showEditPlaceForm(placeData) {
    this.hideOverlays();
    const data =
      typeof placeData === "string" ? JSON.parse(placeData) : placeData;
    if (editPlaceForm.populateForm(data)) {
      this.elements.editPlaceSection.style.display = "block";
      tagInput.init("edit-tags-input", this.state.allUserTags);
      tagInput.setTags("edit-tags-input", data.tags || []);
    }
  },

  hideEditPlaceForm() {
    this.elements.editPlaceSection.style.display = "none";
    pinningUI.deactivatePinning();
  },

  showPlanVisitForm(placeData, visitToEdit = null) {
    this.hideOverlays();
    const data =
      typeof placeData === "string" ? JSON.parse(placeData) : placeData;
    if (visitForm.populateForm(data, visitToEdit)) {
      this.elements.planVisitSection.style.display = "block";
    }
  },

  showVisitReviewForm(visitData, placeName) {
    this.hideOverlays();
    const data =
      typeof visitData === "string" ? JSON.parse(visitData) : visitData;
    if (reviewForm.populateForm(data, placeName)) {
      this.elements.visitReviewImageSection.style.display = "block";
    }
  },

  async showVisitsListModal(placeData) {
    this.hideOverlays();
    const data =
      typeof placeData === "string" ? JSON.parse(placeData) : placeData;
    this.elements.visitsListPlaceTitle.textContent = data.name;
    this.elements.visitsListModal.style.display = "block";

    try {
      const response = await apiClient.get(`/api/v1/places/${data.id}/visits`);
      if (response.ok) {
        const visits = await response.json();
        this.renderVisitsList(visits, data);
      }
    } catch (e) {
      console.error("Failed to load visits", e);
    }
  },

  renderVisitsList(visits, placeData) {
    const content = document.getElementById("visits-list-content");
    if (!content) return;

    if (visits.length === 0) {
      content.innerHTML = "<p>No visits scheduled yet.</p>";
      return;
    }

    content.innerHTML = `<ul class="visits-ul">
            ${visits
              .map(
                (v) => `
                <li class="visit-item">
                    <strong>${new Date(v.visit_datetime).toLocaleDateString()}</strong>
                    <div class="visit-item-actions">
                        <button onclick='window.showPlanVisitForm(${JSON.stringify(placeData)}, ${JSON.stringify(v)})' class="small-btn secondary-btn">Edit</button>
                        <button onclick='window.showVisitReviewForm(${JSON.stringify(v)}, "${placeData.name}")' class="small-btn primary-btn">Review</button>
                    </div>
                </li>
            `,
              )
              .join("")}
        </ul>`;
  },
};

export default uiOrchestrator;
