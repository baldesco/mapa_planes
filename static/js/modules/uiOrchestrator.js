/**
 * uiOrchestrator.js
 * Handles the high-level orchestration of UI sections and initializes specific form/component modules.
 * Now operates as a State Manager for SPA-Lite behavior, coordinating with mapHandler.
 */

import addPlaceForm from "./forms/addPlaceForm.js";
import editPlaceForm from "./forms/editPlaceForm.js";
import reviewForm from "./forms/reviewForm.js";
import visitForm from "./forms/visitForm.js";
import icsCustomizeForm from "./forms/icsCustomizeForm.js";
import modals from "./components/modals.js";
import pinningUI from "./components/pinningUI.js";
import mapHandler from "./mapHandler.js";
import tagInput from "./components/tagInput.js";
import { setStatusMessage } from "./components/statusMessages.js";
import apiClient from "./apiClient.js";

function debounce(func, wait) {
  let timeout;
  return function executedFunction(...args) {
    const later = () => {
      clearTimeout(timeout);
      func(...args);
    };
    clearTimeout(timeout);
    timeout = setTimeout(later, wait);
  };
}

const uiOrchestrator = {
  elements: {
    toggleAddPlaceBtn: null,
    addPlaceWrapper: null,
    editPlaceSection: null,
    visitReviewImageSection: null,
    seeVisitReviewSection: null,
    planVisitSection: null,
    visitsListModal: null,
    visitsListContent: null,
    visitsListPlaceTitle: null,
    visitsListStatus: null,
    visitsListCloseBtn: null,
    visitsListPlanNewBtn: null,
    icsCustomizeModal: null,
    mapContainer: null,
    tagFilterInput: null,
    editTagsInput: null,
  },
  isMapReady: false,
  debouncedInvalidateMapSize: null,
  allUserTags: [],
  currentPlaceForVisitModal: null,
  state: {
    places: [], // Single source of truth for the UI
  },

  init() {
    this.cacheDOMElements();
    this.loadUserTags();
    this.hideAllSectionsAndModals();

    // 1. Initialize Map from embedded JSON and populate state
    const mapDataElement = document.getElementById("map-data");
    if (mapDataElement) {
      try {
        const mapData = JSON.parse(mapDataElement.textContent || "{}");
        this.state.places = mapData.places || [];
        this.isMapReady = mapHandler.initMainMap("map", mapData);
      } catch (e) {
        console.error("UI Orchestrator: Failed to parse map data JSON:", e);
      }
    }

    // 2. Initialize Forms and Components with new state callbacks
    addPlaceForm.init(
      this.isMapReady,
      this.showAddPlaceForm.bind(this),
      this.hideAddPlaceForm.bind(this),
      this.handlePlaceAdded.bind(this),
    );
    editPlaceForm.init(
      this.isMapReady,
      this.showEditPlaceForm.bind(this),
      this.hideEditPlaceForm.bind(this),
      this.handlePlaceUpdated.bind(this),
    );
    reviewForm.init(this.hideVisitReviewForm.bind(this), (savedData) =>
      this.handleVisitSaved(savedData, "reviewForm"),
    );
    visitForm.init(this.hidePlanVisitForm.bind(this), (savedData) =>
      this.handleVisitSaved(savedData, "visitForm"),
    );
    icsCustomizeForm.init(this.hideIcsCustomizeModal.bind(this));
    modals.init(this.showVisitReviewForm.bind(this));
    pinningUI.init(this.isMapReady);

    // 3. Initialize Tag Filters
    if (this.elements.tagFilterInput) {
      tagInput.init("tag-filter-input", this.allUserTags, {
        editTags: false,
        placeholder: "Filter by tags...",
        hooks: {
          add: [() => document.getElementById("filter-form")?.submit()],
          remove: [() => document.getElementById("filter-form")?.submit()],
        },
      });
    }

    this.setupEventListeners();

    // 4. Global bindings for marker popups (Native Leaflet strategy)
    window.showEditPlaceForm = this.showEditPlaceForm.bind(this);
    window.showPlanVisitForm = this.showPlanVisitForm.bind(this);
    window.showVisitsListModal = this.showVisitsListModal.bind(this);
    window.showSeeVisitReviewModal = modals.showSeeReviewModal.bind(modals);
    window.showVisitReviewForm = this.showVisitReviewForm.bind(this);
    window.showIcsCustomizeModal = this.showIcsCustomizeModal.bind(this);
    window.showImageOverlay = modals.showImageOverlay.bind(modals);
    window.deletePlace = this.handleDeletePlace.bind(this); // Expose for map popup

    if (this.isMapReady) {
      this.setupResizeObserver();
      this.setupMapClickHandling();
    }
  },

  cacheDOMElements() {
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

    if (this.elements.visitsListModal) {
      this.elements.visitsListContent = document.getElementById(
        "visits-list-content",
      );
      this.elements.visitsListPlaceTitle = document.getElementById(
        "visits-list-place-title",
      );
      this.elements.visitsListStatus =
        document.getElementById("visits-list-status");
      this.elements.visitsListCloseBtn = document.getElementById(
        "visits-list-close-btn",
      );
      this.elements.visitsListPlanNewBtn = document.getElementById(
        "visits-list-plan-new-btn",
      );
    }

    this.elements.icsCustomizeModal = document.getElementById(
      "ics-customize-modal",
    );
    this.elements.mapContainer = document.getElementById("map");
    this.elements.tagFilterInput = document.getElementById("tag-filter-input");
    this.elements.editTagsInput = document.getElementById("edit-tags-input");
  },

  loadUserTags() {
    const tagsDataElement = document.getElementById("user-tags-data");
    if (tagsDataElement) {
      try {
        const tagsData = JSON.parse(tagsDataElement.textContent || "[]");
        this.allUserTags = tagsData.map((tag) => tag.name);
      } catch (e) {
        console.error(
          "UI Orchestrator: Failed to parse embedded user tags data:",
          e,
        );
        this.allUserTags = [];
      }
    }
  },

  setupResizeObserver() {
    if (!this.elements.mapContainer) return;
    this.debouncedInvalidateMapSize = debounce(
      mapHandler.invalidateMapSize.bind(mapHandler),
      250,
    );
    const resizeObserver = new ResizeObserver(() => {
      this.debouncedInvalidateMapSize();
    });
    resizeObserver.observe(this.elements.mapContainer);
  },

  setupMapClickHandling() {
    const map = mapHandler.getMainMap();
    if (map) {
      map.on("click", (e) => {
        if (pinningUI.isActive && pinningUI.updateCoordsCallback) {
          pinningUI.updateCoordsCallback({
            latitude: e.latlng.lat,
            longitude: e.latlng.lng,
          });
        }
      });
    }
  },

  setupEventListeners() {
    if (this.elements.toggleAddPlaceBtn) {
      this.elements.toggleAddPlaceBtn.addEventListener("click", () => {
        const isHidden =
          !this.elements.addPlaceWrapper ||
          this.elements.addPlaceWrapper.style.display === "none" ||
          this.elements.addPlaceWrapper.style.display === "";
        if (isHidden) this.showAddPlaceForm();
        else this.hideAddPlaceForm();
      });
    }
    if (this.elements.visitsListCloseBtn) {
      this.elements.visitsListCloseBtn.addEventListener("click", () =>
        this.hideVisitsListModal(),
      );
    }
    if (this.elements.visitsListPlanNewBtn) {
      this.elements.visitsListPlanNewBtn.addEventListener("click", () => {
        const placeData = this.currentPlaceForVisitModal;
        if (placeData && placeData.id) {
          this.hideVisitsListModal();
          this.showPlanVisitForm(placeData, null);
        }
      });
    }
  },

  hideAllSectionsAndModals() {
    const sections = [
      this.elements.addPlaceWrapper,
      this.elements.editPlaceSection,
      this.elements.visitReviewImageSection,
      this.elements.seeVisitReviewSection,
      this.elements.planVisitSection,
      this.elements.visitsListModal,
      this.elements.icsCustomizeModal,
    ];
    sections.forEach((s) => {
      if (s) s.style.display = "none";
    });

    pinningUI.deactivatePinning();
    if (this.elements.toggleAddPlaceBtn)
      this.elements.toggleAddPlaceBtn.textContent = "Add New Place";
    tagInput.destroy("edit-tags-input");
  },

  // --- UI Visibility Toggles ---

  showAddPlaceForm() {
    this.hideAllSectionsAndModals();
    addPlaceForm.resetForm();
    if (this.elements.addPlaceWrapper) {
      this.elements.addPlaceWrapper.style.display = "block";
      if (this.elements.toggleAddPlaceBtn)
        this.elements.toggleAddPlaceBtn.textContent = "Cancel Adding";
      this.elements.addPlaceWrapper.scrollIntoView({
        behavior: "smooth",
        block: "start",
      });
    }
  },

  hideAddPlaceForm() {
    if (this.elements.addPlaceWrapper)
      this.elements.addPlaceWrapper.style.display = "none";
    if (this.elements.toggleAddPlaceBtn)
      this.elements.toggleAddPlaceBtn.textContent = "Add New Place";
    pinningUI.deactivateIfActiveFor("add");
  },

  showEditPlaceForm(placeDataInput) {
    let placeData =
      typeof placeDataInput === "string"
        ? JSON.parse(placeDataInput)
        : placeDataInput;
    if (!placeData || !placeData.id) return;

    this.hideAllSectionsAndModals();
    if (editPlaceForm.populateForm(placeData)) {
      if (this.elements.editPlaceSection) {
        this.elements.editPlaceSection.style.display = "block";
        if (this.elements.editTagsInput) {
          tagInput.init("edit-tags-input", this.allUserTags, {
            placeholder: "Add tags...",
          });
          tagInput.setTags("edit-tags-input", placeData.tags || []);
        }
        this.elements.editPlaceSection.scrollIntoView({
          behavior: "smooth",
          block: "start",
        });
      }
    }
  },

  hideEditPlaceForm() {
    if (this.elements.editPlaceSection)
      this.elements.editPlaceSection.style.display = "none";
    pinningUI.deactivateIfActiveFor("edit");
    tagInput.destroy("edit-tags-input");
  },

  showPlanVisitForm(placeDataInput, visitToEdit = null) {
    let placeData =
      typeof placeDataInput === "string"
        ? JSON.parse(placeDataInput)
        : placeDataInput;
    if (!placeData || !placeData.id) return;

    this.hideAllSectionsAndModals();
    if (visitForm.populateForm(placeData, visitToEdit)) {
      if (this.elements.planVisitSection) {
        this.elements.planVisitSection.style.display = "block";
        this.elements.planVisitSection.scrollIntoView({
          behavior: "smooth",
          block: "start",
        });
      }
    }
  },

  hidePlanVisitForm() {
    if (this.elements.planVisitSection)
      this.elements.planVisitSection.style.display = "none";
  },

  showVisitReviewForm(visitDataInput, placeName = "this place") {
    let visitData =
      typeof visitDataInput === "string"
        ? JSON.parse(visitDataInput)
        : visitDataInput;
    if (!visitData || !visitData.id) return;

    this.hideAllSectionsAndModals();
    if (reviewForm.populateForm(visitData, placeName)) {
      if (this.elements.visitReviewImageSection) {
        this.elements.visitReviewImageSection.style.display = "block";
        this.elements.visitReviewImageSection.scrollIntoView({
          behavior: "smooth",
          block: "start",
        });
      }
    }
  },

  hideVisitReviewForm() {
    if (this.elements.visitReviewImageSection)
      this.elements.visitReviewImageSection.style.display = "none";
  },

  // --- SPA State Handlers ---

  handlePlaceAdded(newPlace) {
    this.state.places.unshift(newPlace);
    mapHandler.renderMarkers(this.state.places);
    this.hideAddPlaceForm();
    if (newPlace.latitude && newPlace.longitude) {
      mapHandler.flyTo(newPlace.latitude, newPlace.longitude);
    }
  },

  handlePlaceUpdated(updatedPlace) {
    const index = this.state.places.findIndex((p) => p.id === updatedPlace.id);
    if (index !== -1) {
      this.state.places[index] = updatedPlace;
    } else {
      this.state.places.push(updatedPlace);
    }

    mapHandler.renderMarkers(this.state.places);
    this.hideEditPlaceForm();
    this.hideVisitReviewForm();
    this.hidePlanVisitForm();

    // Close any open popups so the user can click the new marker for fresh data
    const map = mapHandler.getMainMap();
    if (map) map.closePopup();
  },

  async handleDeletePlace(placeId) {
    if (!confirm("Delete this place and all its visits?")) return;

    // Close the popup immediately to provide snappy UI feedback
    const map = mapHandler.getMainMap();
    if (map) map.closePopup();

    try {
      const response = await apiClient.delete(`/api/v1/places/${placeId}`);
      if (response.ok || response.status === 204) {
        this.state.places = this.state.places.filter((p) => p.id !== placeId);
        mapHandler.renderMarkers(this.state.places);
      } else {
        alert("Failed to delete place. Please try again.");
      }
    } catch (error) {
      console.error("Error deleting place:", error);
      alert("An error occurred while deleting the place.");
    }
  },

  async handleVisitSaved(savedVisitData, sourceForm = "unknown") {
    try {
      // Re-fetch the parent place to get updated status and hydrated visits array
      const response = await apiClient.get(
        `/api/v1/places/${savedVisitData.place_id}`,
      );
      if (response.ok) {
        const updatedPlace = await response.json();
        this.handlePlaceUpdated(updatedPlace);

        // If the visits list modal happens to be open, update its content in place
        if (
          this.elements.visitsListModal &&
          this.elements.visitsListModal.style.display === "block" &&
          this.currentPlaceForVisitModal?.id === updatedPlace.id
        ) {
          this.currentPlaceForVisitModal = updatedPlace;
          this.renderVisitsList(updatedPlace.visits || [], updatedPlace);
        }
      }
    } catch (error) {
      console.error("Failed to fetch updated place after visit save:", error);
    }
  },

  async handleDeleteVisit(visitId) {
    if (!confirm("Delete this visit?")) return;
    setStatusMessage(this.elements.visitsListStatus, "Deleting...", "loading");
    try {
      const response = await apiClient.delete(`/api/v1/visits/${visitId}`);
      if (response.ok || response.status === 204) {
        // Must fetch the place again because deleting a visit might have altered its PlaceStatus
        if (this.currentPlaceForVisitModal) {
          const placeId = this.currentPlaceForVisitModal.id;
          const placeResponse = await apiClient.get(
            `/api/v1/places/${placeId}`,
          );
          if (placeResponse.ok) {
            const updatedPlace = await placeResponse.json();
            this.handlePlaceUpdated(updatedPlace);
            this.currentPlaceForVisitModal = updatedPlace;
            this.renderVisitsList(updatedPlace.visits || [], updatedPlace);
            setStatusMessage(
              this.elements.visitsListStatus,
              "Visit deleted.",
              "success",
            );

            // Remove success message after a short delay
            setTimeout(() => {
              setStatusMessage(this.elements.visitsListStatus, "", "info");
            }, 3000);
          }
        }
      } else {
        setStatusMessage(
          this.elements.visitsListStatus,
          "Failed to delete visit.",
          "error",
        );
      }
    } catch (error) {
      setStatusMessage(
        this.elements.visitsListStatus,
        "Error deleting visit.",
        "error",
      );
    }
  },

  // --- Modals logic ---

  async showVisitsListModal(placeDataInput) {
    let placeData =
      typeof placeDataInput === "string"
        ? JSON.parse(placeDataInput)
        : placeDataInput;
    if (!placeData || !placeData.id) return;

    this.currentPlaceForVisitModal = placeData;
    this.hideAllSectionsAndModals();

    this.elements.visitsListPlaceTitle.textContent = `"${placeData.name || "Unknown Place"}"`;
    this.elements.visitsListContent.innerHTML = "<p>Loading visits...</p>";
    setStatusMessage(this.elements.visitsListStatus, "", "info");
    this.elements.visitsListModal.style.display = "block";
    this.elements.visitsListModal.scrollIntoView({
      behavior: "smooth",
      block: "center",
    });

    try {
      const response = await apiClient.get(
        `/api/v1/places/${placeData.id}/visits`,
      );
      if (response.ok) {
        const visits = await response.json();
        this.renderVisitsList(visits, placeData);
      }
    } catch (error) {
      this.elements.visitsListContent.innerHTML = `<p class="error-message">Could not load visits.</p>`;
    }
  },

  hideVisitsListModal() {
    if (this.elements.visitsListModal)
      this.elements.visitsListModal.style.display = "none";
    this.currentPlaceForVisitModal = null;
  },

  renderVisitsList(visits, placeData) {
    if (!this.elements.visitsListContent) return;
    if (!visits || visits.length === 0) {
      this.elements.visitsListContent.innerHTML =
        "<p>No visits recorded yet.</p>";
      return;
    }

    let html = '<ul class="visits-ul">';
    const now = new Date();

    visits.forEach((visit) => {
      const visitDate = new Date(visit.visit_datetime);
      const isFuture = visitDate >= now;
      const formattedDate = visitDate.toLocaleDateString(undefined, {
        year: "numeric",
        month: "long",
        day: "numeric",
      });
      const formattedTime = visitDate.toLocaleTimeString(undefined, {
        hour: "2-digit",
        minute: "2-digit",
      });

      const visitJson = JSON.stringify(visit).replace(/'/g, "&apos;");
      const placeJson = JSON.stringify(placeData).replace(/'/g, "&apos;");
      const placeNameAttr = JSON.stringify(
        placeData.name || "this place",
      ).replace(/'/g, "&apos;");

      html += `<li class="visit-item ${isFuture ? "future-visit" : ""}">
                <strong>${formattedDate} at ${formattedTime}</strong> 
                ${isFuture ? '<span class="future-tag">(Upcoming)</span>' : ""}<br>
                ${visit.review_title ? `<em>${this.escapeHTML(visit.review_title)}</em><br>` : ""}
                <div class="visit-item-actions">
                    <button type="button" class="small-btn edit-visit-schedule-btn" data-visit='${visitJson}'>Edit</button>
                    <button type="button" class="small-btn review-visit-btn" data-visit='${visitJson}' data-placename='${placeNameAttr}'>
                        ${visit.review_title || visit.rating ? "See Review" : "Add Review"}
                    </button>
                    <button type="button" class="small-btn delete-visit-btn" data-visit-id="${visit.id}">Delete</button>
                    ${isFuture ? `<button type="button" class="small-btn add-to-calendar-btn" data-visit='${visitJson}' data-place='${placeJson}'>Calendar</button>` : ""}
                </div>
            </li>`;
    });
    html += "</ul>";
    this.elements.visitsListContent.innerHTML = html;

    this.elements.visitsListContent
      .querySelectorAll(".edit-visit-schedule-btn")
      .forEach((btn) => {
        btn.addEventListener("click", (e) => {
          const data = JSON.parse(e.currentTarget.dataset.visit);
          this.hideVisitsListModal();
          this.showPlanVisitForm(this.currentPlaceForVisitModal, data);
        });
      });

    this.elements.visitsListContent
      .querySelectorAll(".review-visit-btn")
      .forEach((btn) => {
        btn.addEventListener("click", (e) => {
          const visitData = JSON.parse(e.currentTarget.dataset.visit);
          const placeName = JSON.parse(e.currentTarget.dataset.placename);
          this.hideVisitsListModal();
          if (visitData.review_title || visitData.rating)
            modals.showSeeReviewModal(visitData, placeName);
          else this.showVisitReviewForm(visitData, placeName);
        });
      });

    this.elements.visitsListContent
      .querySelectorAll(".delete-visit-btn")
      .forEach((btn) => {
        btn.addEventListener("click", (e) =>
          this.handleDeleteVisit(e.currentTarget.dataset.visitId),
        );
      });

    this.elements.visitsListContent
      .querySelectorAll(".add-to-calendar-btn")
      .forEach((btn) => {
        btn.addEventListener("click", (e) => {
          const visitData = JSON.parse(e.currentTarget.dataset.visit);
          const placeData = JSON.parse(e.currentTarget.dataset.place);
          this.showIcsCustomizeModal(visitData, placeData);
        });
      });
  },

  showIcsCustomizeModal(visitData, placeData) {
    this.hideAllSectionsAndModals();
    if (icsCustomizeForm.populateForm(visitData, placeData)) {
      if (this.elements.icsCustomizeModal) {
        this.elements.icsCustomizeModal.style.display = "block";
        this.elements.icsCustomizeModal.scrollIntoView({
          behavior: "smooth",
          block: "center",
        });
      }
    }
  },

  hideIcsCustomizeModal() {
    if (this.elements.icsCustomizeModal)
      this.elements.icsCustomizeModal.style.display = "none";
  },

  escapeHTML(str) {
    if (!str) return "";
    return String(str).replace(
      /[&<>"']/g,
      (m) =>
        ({
          "&": "&amp;",
          "<": "&lt;",
          ">": "&gt;",
          '"': "&quot;",
          "'": "&#039;",
        })[m],
    );
  },
};

export default uiOrchestrator;
