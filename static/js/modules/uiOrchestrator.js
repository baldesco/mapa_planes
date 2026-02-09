/**
 * uiOrchestrator.js
 * Central manager for application state, filtering, and sorting.
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
import apiClient from "./apiClient.js";

const uiOrchestrator = {
  state: {
    allPlaces: [],
    filteredPlaces: [],
    allUserTags: [],
    filters: { search: "", category: "", status: "", tags: [] },
    sortBy: "newest",
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
    toggleSidebarBtn: null,
    sidebar: null,
    sortSelect: null,
    addPlaceWrapper: null,
    editPlaceSection: null,
    visitReviewImageSection: null,
    seeVisitReviewSection: null,
    planVisitSection: null,
    visitsListModal: null,
    icsCustomizeModal: null,
    visitsListPlaceTitle: null,
  },

  init() {
    this.cacheDOMElements();
    this.loadInitialData();

    const mapDataElement = document.getElementById("map-data");
    const mapData = mapDataElement
      ? JSON.parse(mapDataElement.textContent || "{}")
      : {};
    this.state.allPlaces = mapData.places || [];

    const isMapReady = mapHandler.initMainMap("map", mapData);

    sidebar.init(this.handlePlaceSelection.bind(this));

    addPlaceForm.init(
      isMapReady,
      () => this.showAddPlaceForm(),
      () => this.hideOverlays(),
      (newPlace) => this.handlePlaceUpdate(newPlace),
    );

    editPlaceForm.init(
      isMapReady,
      () => this.showEditPlaceForm(),
      () => this.hideOverlays(),
      (updatedPlace) => this.handlePlaceUpdate(updatedPlace),
    );

    reviewForm.init(
      () => this.hideOverlays(),
      (updatedVisit) => this.handleVisitUpdate(updatedVisit),
    );

    visitForm.init(
      () => this.hideOverlays(),
      (newVisit) => this.handleVisitUpdate(newVisit),
    );

    icsCustomizeForm.init(() => this.hideOverlays());
    modals.init((v, n) => this.showVisitReviewForm(v, n));
    pinningUI.init(isMapReady);

    this.setupTagFilters();
    this.setupEventListeners();
    this.applyFilters();

    // Bindings for external access (popups, etc.)
    window.showEditPlaceForm = (d) => this.showEditPlaceForm(d);
    window.showPlanVisitForm = (d, v) => this.showPlanVisitForm(d, v);
    window.showVisitsListModal = (d) => this.showVisitsListModal(d);
    window.showSeeVisitReviewModal = (v, n) => modals.showSeeReviewModal(v, n);
    window.showVisitReviewForm = (v, n) => this.showVisitReviewForm(v, n);
    window.showIcsCustomizeModal = (v, p) => this.showIcsCustomizeModal(v, p);
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
    this.elements.toggleSidebarBtn =
      document.getElementById("toggle-sidebar-btn");
    this.elements.sidebar = document.getElementById("sidebar");
    this.elements.sortSelect = document.getElementById("sort-places");

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
    this.elements.visitsListPlaceTitle = document.getElementById(
      "visits-list-place-title",
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
      const tagify = tagInput.init("tag-filter-input", this.state.allUserTags);
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

    this.elements.sortSelect?.addEventListener("change", (e) => {
      this.state.sortBy = e.target.value;
      this.applyFilters();
    });

    this.elements.clearFiltersBtn?.addEventListener("click", () => {
      this.elements.globalSearch.value = "";
      this.elements.categorySelect.value = "";
      this.elements.statusSelect.value = "";
      tagInput.tagifyInstances["tag-filter-input"]?.removeAllTags();
      this.state.filters = { search: "", category: "", status: "", tags: [] };
      this.applyFilters();
    });

    this.elements.toggleFiltersBtn?.addEventListener("click", () => {
      const panel = this.elements.filterPanel;
      panel.style.display = panel.style.display === "none" ? "block" : "none";
    });

    // Sidebar toggle logic with map invalidation
    this.elements.toggleSidebarBtn?.addEventListener("click", () => {
      if (this.elements.sidebar) {
        this.elements.sidebar.classList.toggle("collapsed");
        // We wait for the CSS transition to finish before telling Leaflet to resize
        setTimeout(() => mapHandler.invalidateMapSize(), 310);
      }
    });

    this.elements.toggleAddPlaceBtn?.addEventListener("click", () =>
      this.showAddPlaceForm(),
    );
  },

  applyFilters() {
    const { search, category, status, tags } = this.state.filters;

    let filtered = this.state.allPlaces.filter((place) => {
      const matchesSearch =
        !search ||
        place.name.toLowerCase().includes(search) ||
        (place.address && place.address.toLowerCase().includes(search));
      const matchesCategory = !category || place.category === category;
      const matchesStatus = !status || place.status === status;
      const matchesTags =
        tags.length === 0 ||
        (place.tags || []).some((pt) =>
          tags.includes((pt.name || pt).toLowerCase()),
        );

      return matchesSearch && matchesCategory && matchesStatus && matchesTags;
    });

    const sortBy = this.state.sortBy;
    filtered.sort((a, b) => {
      if (sortBy === "name_asc") return a.name.localeCompare(b.name);
      if (sortBy === "name_desc") return b.name.localeCompare(a.name);
      if (sortBy === "newest")
        return new Date(b.created_at) - new Date(a.created_at);
      if (sortBy === "rating") {
        const getRating = (p) =>
          (p.visits || []).find((v) => v.rating)?.rating || 0;
        return getRating(b) - getRating(a);
      }
      return 0;
    });

    this.state.filteredPlaces = filtered;
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

  handlePlaceUpdate(updatedPlace) {
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
    try {
      const response = await apiClient.get(
        `/api/v1/places/${updatedVisit.place_id}`,
      );
      if (response.ok) {
        const updatedPlace = await response.json();
        this.handlePlaceUpdate(updatedPlace);
      }
    } catch (e) {
      console.error("Sync error", e);
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

  showEditPlaceForm(placeData) {
    const data =
      typeof placeData === "string" ? JSON.parse(placeData) : placeData;
    this.hideOverlays();
    if (editPlaceForm.populateForm(data)) {
      this.elements.editPlaceSection.style.display = "block";
      tagInput.init("edit-tags-input", this.state.allUserTags);
      tagInput.setTags("edit-tags-input", data.tags || []);
    }
  },

  showPlanVisitForm(placeData, visitToEdit = null) {
    const pData =
      typeof placeData === "string" ? JSON.parse(placeData) : placeData;
    const vData = visitToEdit
      ? typeof visitToEdit === "string"
        ? JSON.parse(visitToEdit)
        : visitToEdit
      : null;
    this.hideOverlays();
    if (visitForm.populateForm(pData, vData)) {
      this.elements.planVisitSection.style.display = "block";
    }
  },

  showVisitReviewForm(visitData, placeName) {
    const vData =
      typeof visitData === "string" ? JSON.parse(visitData) : visitData;
    this.hideOverlays();
    if (reviewForm.populateForm(vData, placeName)) {
      this.elements.visitReviewImageSection.style.display = "block";
    }
  },

  showIcsCustomizeModal(visitData, placeData) {
    const vData =
      typeof visitData === "string" ? JSON.parse(visitData) : visitData;
    const pData =
      typeof placeData === "string" ? JSON.parse(placeData) : placeData;
    this.hideOverlays();
    if (icsCustomizeForm.populateForm(vData, pData)) {
      this.elements.icsCustomizeModal.style.display = "block";
    }
  },

  async showVisitsListModal(placeData) {
    const data =
      typeof placeData === "string" ? JSON.parse(placeData) : placeData;
    this.hideOverlays();
    this.elements.visitsListPlaceTitle.textContent = data.name;
    this.elements.visitsListModal.style.display = "block";

    try {
      const response = await apiClient.get(`/api/v1/places/${data.id}/visits`);
      if (response.ok) {
        const visits = await response.json();
        this.renderVisitsList(visits, data);
      }
    } catch (e) {
      console.error("Load error", e);
    }
  },

  renderVisitsList(visits, placeData) {
    const content = document.getElementById("visits-list-content");
    if (!content) return;
    if (visits.length === 0) {
      content.innerHTML = "<p>No visits scheduled.</p>";
      return;
    }

    content.innerHTML = `<ul class="visits-ul">
            ${visits
              .map((v) => {
                const vJson = JSON.stringify(v).replace(/"/g, "&quot;");
                const pJson = JSON.stringify(placeData).replace(/"/g, "&quot;");
                return `
                <li class="visit-item">
                    <strong>${new Date(v.visit_datetime).toLocaleDateString()}</strong>
                    <div class="visit-item-actions">
                        <button onclick='window.showPlanVisitForm(${pJson}, ${vJson})' class="small-btn secondary-btn">Edit</button>
                        <button onclick='window.showVisitReviewForm(${vJson}, "${placeData.name}")' class="small-btn primary-btn">Review</button>
                    </div>
                </li>`;
              })
              .join("")}
        </ul>`;
  },
};

window.handlePlaceDeleted = (placeId) => {
  uiOrchestrator.state.allPlaces = uiOrchestrator.state.allPlaces.filter(
    (p) => p.id !== placeId,
  );
  uiOrchestrator.applyFilters();
};

export default uiOrchestrator;
