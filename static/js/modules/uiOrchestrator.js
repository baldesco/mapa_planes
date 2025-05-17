/**
 * uiOrchestrator.js
 * Handles the high-level orchestration of UI sections (Add/Edit/Review forms, Modals)
 * on the main page, and initializes specific form/component modules.
 */

import addPlaceForm from "./forms/addPlaceForm.js";
import editPlaceForm from "./forms/editPlaceForm.js";
import reviewForm from "./forms/reviewForm.js";
import visitForm from "./forms/visitForm.js";
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
    mapContainer: null,
    mapIframe: null,
    pinningMapContainer: null,
    tagFilterInput: null,
    editTagsInput: null,
  },
  isMapReady: false,
  debouncedInvalidateMapSize: null,
  allUserTags: [],
  currentPlaceForVisitModal: null,

  init(mapReadyStatus = false) {
    this.isMapReady = mapReadyStatus;
    this.cacheDOMElements();
    this.loadUserTags();
    this.hideAllSectionsAndModals();

    addPlaceForm.init(
      this.isMapReady,
      this.showAddPlaceForm.bind(this),
      this.hideAddPlaceForm.bind(this)
    );
    editPlaceForm.init(
      this.isMapReady,
      this.showEditPlaceForm.bind(this),
      this.hideEditPlaceForm.bind(this)
    );
    reviewForm.init(
      this.hideVisitReviewForm.bind(this),
      this.handleVisitSaved.bind(this)
    );
    visitForm.init(
      this.hidePlanVisitForm.bind(this),
      this.handleVisitSaved.bind(this)
    );
    modals.init(this.showVisitReviewForm.bind(this));
    pinningUI.init(this.isMapReady);

    if (this.elements.tagFilterInput) {
      tagInput.init("tag-filter-input", this.allUserTags, {
        editTags: false,
        placeholder: "Filter by tags...",
        hooks: {
          add: [
            () => {
              document.getElementById("filter-form")?.submit();
            },
          ],
          remove: [
            () => {
              document.getElementById("filter-form")?.submit();
            },
          ],
        },
      });
    }

    this.setupEventListeners();

    window.attachMapClickListener = this.attachMapClickListener.bind(this);
    window.isPinningActive = () => pinningUI.isActive;
    window.handleMapPinClick = this.handleMapPinClick.bind(this);
    window.showEditPlaceForm = this.showEditPlaceForm.bind(this);
    window.showImageOverlay = modals.showImageOverlay.bind(this);
    window.showPlanVisitForm = this.showPlanVisitForm.bind(this);
    window.showVisitsListModal = this.showVisitsListModal.bind(this);
    window.showSeeVisitReviewModal = modals.showSeeReviewModal.bind(modals);
    window.showVisitReviewForm = this.showVisitReviewForm.bind(this);

    if (this.isMapReady && this.elements.mapContainer) {
      this.setupResizeObserver();
    }
    // console.log("UI Orchestrator: Initialization complete."); // Production: remove or make conditional
  },

  cacheDOMElements() {
    this.elements.toggleAddPlaceBtn = document.getElementById(
      "toggle-add-place-form-btn"
    );
    this.elements.addPlaceWrapper = document.getElementById(
      "add-place-wrapper-section"
    );
    this.elements.editPlaceSection =
      document.getElementById("edit-place-section");
    this.elements.visitReviewImageSection = document.getElementById(
      "visit-review-image-section"
    );
    this.elements.seeVisitReviewSection = document.getElementById(
      "see-visit-review-section"
    );
    this.elements.planVisitSection =
      document.getElementById("plan-visit-section");
    this.elements.visitsListModal =
      document.getElementById("visits-list-modal");
    if (this.elements.visitsListModal) {
      this.elements.visitsListContent = document.getElementById(
        "visits-list-content"
      );
      this.elements.visitsListPlaceTitle = document.getElementById(
        "visits-list-place-title"
      );
      this.elements.visitsListStatus =
        document.getElementById("visits-list-status");
      this.elements.visitsListCloseBtn = document.getElementById(
        "visits-list-close-btn"
      );
      this.elements.visitsListPlanNewBtn = document.getElementById(
        "visits-list-plan-new-btn"
      );
    }
    this.elements.mapContainer = document.getElementById("map");
    if (this.elements.mapContainer) {
      this.elements.mapIframe =
        this.elements.mapContainer.querySelector("iframe");
    }
    this.elements.pinningMapContainer = document.getElementById(
      "pinning-map-container"
    );
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
        console.error("Failed to parse embedded user tags data:", e);
        this.allUserTags = [];
      }
    } else {
      // console.warn("User tags data element not found."); // Production: remove or make conditional
      this.allUserTags = [];
    }
  },

  setupResizeObserver() {
    if (!this.elements.mapContainer) return;
    this.debouncedInvalidateMapSize = debounce(
      mapHandler.invalidateMapSize.bind(mapHandler),
      250
    );
    const resizeObserver = new ResizeObserver(() => {
      this.debouncedInvalidateMapSize();
    });
    resizeObserver.observe(this.elements.mapContainer);
  },

  attachMapClickListener(mapVarName) {
    if (!this.elements.mapIframe || !this.elements.mapIframe.contentWindow) {
      console.error(
        "Cannot attach listener: Map iframe or its contentWindow not found."
      );
      return;
    }
    const iframeWindow = this.elements.mapIframe.contentWindow;
    const tryAttach = () => {
      try {
        const mapInstance = iframeWindow[mapVarName];
        if (mapInstance && typeof mapInstance.on === "function") {
          const listener = (e) => {
            if (window.isPinningActive()) {
              window.handleMapPinClick(e.latlng.lat, e.latlng.lng);
            }
          };
          mapInstance.on("click", listener);
          return true;
        }
        return false;
      } catch (err) {
        console.error(
          `Error attaching map click listener to '${mapVarName}':`,
          err
        );
        return false;
      }
    };
    if (!tryAttach()) {
      setTimeout(() => {
        if (!tryAttach()) {
          console.error(
            `Failed to attach listener to '${mapVarName}' even after delay.`
          );
        }
      }, 1500);
    }
  },

  handleMapPinClick(lat, lng) {
    if (!pinningUI.isActive || !pinningUI.updateCoordsCallback) {
      // console.warn("handleMapPinClick called but pinning not active or callback missing."); // Production: remove
      return;
    }
    pinningUI.updateCoordsCallback({ latitude: lat, longitude: lng });
  },

  setupEventListeners() {
    if (this.elements.toggleAddPlaceBtn) {
      this.elements.toggleAddPlaceBtn.addEventListener("click", () => {
        const isHidden =
          !this.elements.addPlaceWrapper ||
          this.elements.addPlaceWrapper.style.display === "none" ||
          this.elements.addPlaceWrapper.style.display === "";
        if (isHidden) {
          this.showAddPlaceForm();
        } else {
          this.hideAddPlaceForm();
        }
      });
    }
    if (this.elements.visitsListCloseBtn) {
      this.elements.visitsListCloseBtn.addEventListener("click", () =>
        this.hideVisitsListModal()
      );
    }
    if (this.elements.visitsListPlanNewBtn) {
      const self = this;
      this.elements.visitsListPlanNewBtn.addEventListener("click", () => {
        const placeDataForCall = self.currentPlaceForVisitModal;
        if (placeDataForCall && placeDataForCall.id) {
          self.hideVisitsListModal();
          const clonedPlaceData = JSON.parse(JSON.stringify(placeDataForCall));
          self.showPlanVisitForm(clonedPlaceData, null);
        } else {
          alert(
            "Error: Place context lost or invalid for planning another visit (pre-call check)."
          );
          console.error(
            "Plan Another Visit: placeDataForCall is null, undefined, or lacks an ID.",
            placeDataForCall
          );
        }
      });
    }
  },

  hideAllSectionsAndModals() {
    // console.debug("UI Orchestrator: Hiding all sections and modals."); // Production: remove
    if (this.elements.addPlaceWrapper)
      this.elements.addPlaceWrapper.style.display = "none";
    if (this.elements.editPlaceSection)
      this.elements.editPlaceSection.style.display = "none";
    if (this.elements.visitReviewImageSection)
      this.elements.visitReviewImageSection.style.display = "none";
    if (this.elements.seeVisitReviewSection)
      this.elements.seeVisitReviewSection.style.display = "none";
    if (this.elements.planVisitSection)
      this.elements.planVisitSection.style.display = "none";
    if (this.elements.visitsListModal)
      this.elements.visitsListModal.style.display = "none";
    pinningUI.deactivatePinning();
    if (this.elements.pinningMapContainer)
      this.elements.pinningMapContainer.style.display = "none";
    if (this.elements.toggleAddPlaceBtn)
      this.elements.toggleAddPlaceBtn.textContent = "Add New Place";
    tagInput.destroy("edit-tags-input");
  },

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
    let placeData;
    try {
      placeData =
        typeof placeDataInput === "string"
          ? JSON.parse(placeDataInput)
          : placeDataInput;
    } catch (e) {
      console.error(
        "showEditPlaceForm: Invalid placeData JSON",
        e,
        "Input was:",
        placeDataInput
      );
      alert("Error preparing edit form: Invalid place data format.");
      return;
    }

    if (!placeData || !placeData.id) {
      console.error(
        "showEditPlaceForm: Invalid or missing place data (or place.id). placeData:",
        placeData
      );
      alert("Cannot edit place without valid information.");
      return;
    }

    this.hideAllSectionsAndModals();
    if (editPlaceForm.populateForm(placeData)) {
      if (this.elements.editPlaceSection) {
        this.elements.editPlaceSection.style.display = "block";
        if (this.elements.toggleAddPlaceBtn)
          this.elements.toggleAddPlaceBtn.textContent = "Add New Place";
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
    } else {
      console.error("UI Orchestrator: Failed to populate edit place form.");
    }
  },

  hideEditPlaceForm() {
    if (this.elements.editPlaceSection)
      this.elements.editPlaceSection.style.display = "none";
    pinningUI.deactivateIfActiveFor("edit");
    tagInput.destroy("edit-tags-input");
  },

  showPlanVisitForm(placeDataInput, visitToEdit = null) {
    let placeData;
    if (typeof placeDataInput === "string") {
      try {
        placeData = JSON.parse(placeDataInput);
      } catch (e) {
        console.error(
          "showPlanVisitForm: Invalid placeData string",
          e,
          "Input was:",
          placeDataInput
        );
        placeData = null;
      }
    } else {
      placeData = placeDataInput;
    }

    if (!placeData || !placeData.id) {
      console.error(
        "showPlanVisitForm: Invalid or missing place data (or place.id) after processing. placeData:",
        placeData
      );
      alert("Cannot plan a visit without valid place information.");
      return;
    }

    this.hideAllSectionsAndModals();
    if (visitForm.populateForm(placeData, visitToEdit)) {
      if (this.elements.planVisitSection) {
        this.elements.planVisitSection.style.display = "block";
        this.elements.planVisitSection.scrollIntoView({
          behavior: "smooth",
          block: "start",
        });
      }
    } else {
      console.error(
        "UI Orchestrator: Failed to populate plan/edit visit form."
      );
    }
  },

  hidePlanVisitForm() {
    if (this.elements.planVisitSection)
      this.elements.planVisitSection.style.display = "none";
  },

  showVisitReviewForm(visitDataInput, placeName = "this place") {
    let visitData;
    try {
      visitData =
        typeof visitDataInput === "string"
          ? JSON.parse(visitDataInput)
          : visitDataInput;
    } catch (e) {
      console.error(
        "showVisitReviewForm: Invalid visitData JSON",
        e,
        "Input was:",
        visitDataInput
      );
      alert("Error preparing review form: Invalid visit data format.");
      return;
    }

    if (!visitData || !visitData.id) {
      console.error(
        "showVisitReviewForm: Invalid or missing visit data (or visit.id). visitData:",
        visitData
      );
      alert("Cannot add/edit review without valid visit information.");
      return;
    }

    this.hideAllSectionsAndModals();
    if (reviewForm.populateForm(visitData, placeName)) {
      if (this.elements.visitReviewImageSection) {
        this.elements.visitReviewImageSection.style.display = "block";
        this.elements.visitReviewImageSection.scrollIntoView({
          behavior: "smooth",
          block: "start",
        });
      }
    } else {
      console.error("UI Orchestrator: Failed to populate visit review form.");
    }
  },

  hideVisitReviewForm() {
    if (this.elements.visitReviewImageSection)
      this.elements.visitReviewImageSection.style.display = "none";
  },

  async showVisitsListModal(placeDataInput) {
    let placeData;
    try {
      placeData =
        typeof placeDataInput === "string"
          ? JSON.parse(placeDataInput)
          : placeDataInput;
    } catch (e) {
      console.error(
        "showVisitsListModal: Invalid placeData JSON",
        e,
        "Input was:",
        placeDataInput
      );
      alert("Error displaying visits: Invalid place data format.");
      return;
    }

    if (
      !placeData ||
      !placeData.id ||
      !this.elements.visitsListModal ||
      !this.elements.visitsListContent ||
      !this.elements.visitsListPlaceTitle ||
      !this.elements.visitsListStatus
    ) {
      console.error(
        "showVisitsListModal: Missing place data or modal elements. placeData:",
        placeData
      );
      return;
    }

    this.currentPlaceForVisitModal = placeData;
    this.hideAllSectionsAndModals();
    this.elements.visitsListPlaceTitle.textContent = `"${
      placeData.name || "Unknown Place"
    }"`;
    this.elements.visitsListContent.innerHTML = "<p>Loading visits...</p>";
    setStatusMessage(this.elements.visitsListStatus, "", "info");
    this.elements.visitsListModal.style.display = "block";
    this.elements.visitsListModal.scrollIntoView({
      behavior: "smooth",
      block: "center",
    });

    try {
      const response = await apiClient.get(
        `/api/v1/places/${placeData.id}/visits`
      );
      if (!response.ok) {
        const errData = await response
          .json()
          .catch(() => ({ detail: "Failed to load visits." }));
        throw new Error(errData.detail || `Error ${response.status}`);
      }
      const visits = await response.json();
      this.renderVisitsList(visits, placeData);
    } catch (error) {
      console.error("Error fetching visits for modal:", error);
      this.elements.visitsListContent.innerHTML = `<p class="error-message">Could not load visits: ${error.message}</p>`;
    }
  },

  hideVisitsListModal() {
    if (this.elements.visitsListModal)
      this.elements.visitsListModal.style.display = "none";
    if (this.elements.visitsListContent)
      this.elements.visitsListContent.innerHTML = "";
    this.currentPlaceForVisitModal = null;
  },

  renderVisitsList(visits, placeData) {
    if (!this.elements.visitsListContent) return;
    if (!visits || visits.length === 0) {
      this.elements.visitsListContent.innerHTML =
        "<p>No visits recorded for this place yet.</p>";
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
      html += `<li class="visit-item ${isFuture ? "future-visit" : ""}">`;
      html += `<strong>${formattedDate} at ${formattedTime}</strong> ${
        isFuture ? '<span class="future-tag">(Upcoming)</span>' : ""
      }<br>`;
      if (visit.review_title) {
        html += `<em>${this.escapeHTML(visit.review_title)}</em><br>`;
      } else if (visit.rating || visit.review_text) {
        html += `<em>(Review present)</em><br>`;
      }
      const visitJson = this.escapeHTML(JSON.stringify(visit));
      const placeNameString = placeData.name || "this place";
      const placeNameAttr = this.escapeHTML(JSON.stringify(placeNameString));
      html += `<div class="visit-item-actions">
                    <button type="button" class="small-btn edit-visit-schedule-btn" data-visit='${visitJson}' title="Edit Visit Date/Time/Reminders">Edit Schedule</button>
                    <button type="button" class="small-btn review-visit-btn" data-visit='${visitJson}' data-placename='${placeNameAttr}' title="Add/Edit Review for this Visit">${
        visit.review_title || visit.review_text || visit.rating
          ? "Edit/See Review"
          : "Add Review"
      }</button>
                    <button type="button" class="small-btn delete-visit-btn" data-visit-id="${
                      visit.id
                    }" title="Delete this Visit">Delete Visit</button>
                 </div></li>`;
    });
    html += "</ul>";
    this.elements.visitsListContent.innerHTML = html;

    this.elements.visitsListContent
      .querySelectorAll(".edit-visit-schedule-btn")
      .forEach((btn) => {
        btn.addEventListener("click", (e) => {
          const visitData = JSON.parse(e.currentTarget.dataset.visit);
          this.hideVisitsListModal();
          if (
            this.currentPlaceForVisitModal &&
            this.currentPlaceForVisitModal.id
          ) {
            this.showPlanVisitForm(this.currentPlaceForVisitModal, visitData);
          } else {
            console.error(
              "Cannot edit visit schedule: Parent place data lost or invalid.",
              this.currentPlaceForVisitModal
            );
            alert(
              "An error occurred: parent place data is missing or invalid."
            );
          }
        });
      });
    this.elements.visitsListContent
      .querySelectorAll(".review-visit-btn")
      .forEach((btn) => {
        btn.addEventListener("click", (e) => {
          const visitData = JSON.parse(e.currentTarget.dataset.visit);
          const placeName = JSON.parse(e.currentTarget.dataset.placename);
          this.hideVisitsListModal();
          if (
            visitData.review_title ||
            visitData.review_text ||
            visitData.rating ||
            visitData.image_url
          ) {
            modals.showSeeReviewModal(visitData, placeName);
          } else {
            this.showVisitReviewForm(visitData, placeName);
          }
        });
      });
    this.elements.visitsListContent
      .querySelectorAll(".delete-visit-btn")
      .forEach((btn) => {
        btn.addEventListener("click", (e) =>
          this.handleDeleteVisit(e.currentTarget.dataset.visitId)
        );
      });
  },

  escapeHTML(str) {
    if (str === null || str === undefined) return "";
    return String(str).replace(/[&<>"']/g, function (match) {
      return { "&": "&", "<": "<", ">": ">", '"': '"', "'": "'" }[match];
    });
  },

  async handleDeleteVisit(visitId) {
    if (!visitId || !this.elements.visitsListStatus) {
      console.error(
        "handleDeleteVisit: visitId or visitsListStatus element is missing."
      );
      return;
    }
    if (
      !confirm(
        "Are you sure you want to delete this visit? This cannot be undone."
      )
    )
      return;

    setStatusMessage(
      this.elements.visitsListStatus,
      "Deleting visit...",
      "loading"
    );
    try {
      const response = await apiClient.delete(`/api/v1/visits/${visitId}`);
      if (response.ok || response.status === 204) {
        setStatusMessage(
          this.elements.visitsListStatus,
          "Visit deleted successfully! Refreshing...",
          "success"
        );
        this.handleVisitSaved(); // This will call window.location.reload()
      } else {
        const errData = await response
          .json()
          .catch(() => ({ detail: "Failed to delete visit." }));
        throw new Error(errData.detail || `Error ${response.status}`);
      }
    } catch (error) {
      console.error("Error deleting visit:", error);
      setStatusMessage(
        this.elements.visitsListStatus,
        `Error: ${error.message}`,
        "error"
      );
    }
  },

  handleVisitSaved(savedVisitData) {
    // console.log("Visit saved/updated, will refresh page to show changes:", savedVisitData); // Production: remove
    window.location.reload();
  },
};

export default uiOrchestrator;
