/**
 * pinningUI.js
 * Manages the UI state and interactions for the map pinning feature.
 * Coordinates with mapHandler.js for native Leaflet map operations.
 */
import mapHandler from "../mapHandler.js";

const pinningUI = {
  elements: {
    addPinBtn: null,
    editPinBtn: null,
    addInstruction: null,
    editInstruction: null,
    mapContainer: null,
    confirmBtn: null,
    cancelBtn: null,
    addStatus: null,
    editStatus: null,
    addPlaceWrapper: null,
    editPlaceSection: null,
  },
  isActive: false,
  activeFormType: null, // 'add' or 'edit'
  updateCoordsCallback: null,
  isMapReady: false,

  init(mapReadyStatus) {
    console.debug("Pinning UI: Initializing...");
    this.isMapReady = mapReadyStatus;
    this.cacheDOMElements();
    this.setupEventListeners();
  },

  cacheDOMElements() {
    this.elements.addPinBtn = document.getElementById("pin-on-map-btn");
    this.elements.editPinBtn = document.getElementById("edit-pin-on-map-btn");
    this.elements.addInstruction = document.getElementById(
      "map-pin-instruction",
    );
    this.elements.editInstruction = document.getElementById(
      "edit-map-pin-instruction",
    );
    this.elements.mapContainer = document.getElementById(
      "pinning-map-container",
    );
    this.elements.confirmBtn = document.getElementById("confirm-pin-btn");
    this.elements.cancelBtn = document.getElementById("cancel-pin-btn");
    this.elements.addStatus = document.getElementById("geocode-status");
    this.elements.editStatus = document.getElementById("edit-geocode-status");
    this.elements.addPlaceWrapper = document.getElementById(
      "add-place-wrapper-section",
    );
    this.elements.editPlaceSection =
      document.getElementById("edit-place-section");
  },

  setupEventListeners() {
    if (this.elements.confirmBtn) {
      this.elements.confirmBtn.addEventListener("click", () =>
        this.confirmPinLocation(),
      );
    }
    if (this.elements.cancelBtn) {
      this.elements.cancelBtn.addEventListener("click", () => {
        if (this.isActive && this.activeFormType) {
          this.deactivatePinning();
        }
      });
    }
  },

  /**
   * Toggles pinning mode for a specific form.
   */
  togglePinning(formType, initialCoords, updateCallback) {
    if (!this.isMapReady) {
      alert("Map functionality is not available.");
      return;
    }

    if (this.isActive && this.activeFormType === formType) {
      this.deactivatePinning();
    } else {
      if (this.isActive) this.deactivatePinning();
      this.activatePinning(formType, initialCoords, updateCallback);
    }
  },

  activatePinning(formType, initialCoords, updateCallback) {
    this.isActive = true;
    this.activeFormType = formType;
    this.updateCoordsCallback = updateCallback;

    const container = this.elements.mapContainer;
    if (!container) return;

    this.moveMapContainer(formType);
    container.style.display = "block";

    if (mapHandler.initPinningMap("pinning-map", initialCoords)) {
      mapHandler.placeDraggableMarker(initialCoords);
      this.updateFormUI(true, formType);
      container.scrollIntoView({ behavior: "smooth", block: "nearest" });
    } else {
      this.deactivatePinning();
    }
  },

  deactivatePinning() {
    if (!this.isActive) return;
    const formType = this.activeFormType;
    this.isActive = false;
    this.activeFormType = null;
    this.updateCoordsCallback = null;

    mapHandler.destroyPinningMap();
    if (this.elements.mapContainer) {
      this.elements.mapContainer.style.display = "none";
    }
    if (formType) {
      this.updateFormUI(false, formType);
    }
  },

  deactivateIfActiveFor(formType) {
    if (this.isActive && this.activeFormType === formType) {
      this.deactivatePinning();
    }
  },

  updateFormUI(isActive, formType) {
    const isEdit = formType === "edit";
    const pinBtn = isEdit ? this.elements.editPinBtn : this.elements.addPinBtn;
    const instructionEl = isEdit
      ? this.elements.editInstruction
      : this.elements.addInstruction;
    const statusEl = isEdit
      ? this.elements.editStatus
      : this.elements.addStatus;

    if (isActive) {
      if (instructionEl) instructionEl.style.display = "block";
      if (pinBtn) pinBtn.textContent = "Cancel Pinning";
      this.setStatusMessage(
        statusEl,
        "Drag the red pin on the map, then confirm.",
        "info",
      );
    } else {
      if (instructionEl) instructionEl.style.display = "none";
      if (pinBtn)
        pinBtn.textContent = isEdit
          ? "Pin New Location"
          : "Pin Location on Map";
    }
  },

  moveMapContainer(formType) {
    const container = this.elements.mapContainer;
    const targetSection =
      formType === "edit"
        ? this.elements.editPlaceSection
        : this.elements.addPlaceWrapper;
    const instruction =
      formType === "edit"
        ? this.elements.editInstruction
        : this.elements.addInstruction;

    if (container && targetSection && instruction) {
      instruction.parentNode.insertBefore(container, instruction.nextSibling);
    }
  },

  confirmPinLocation() {
    if (!this.isActive || !this.updateCoordsCallback) return;

    const position = mapHandler.getDraggableMarkerPosition();
    const statusEl =
      this.activeFormType === "edit"
        ? this.elements.editStatus
        : this.elements.addStatus;

    if (position) {
      this.updateCoordsCallback({
        latitude: position.lat,
        longitude: position.lng,
      });
      this.setStatusMessage(statusEl, "Location set via map pin.", "success");
    }
    this.deactivatePinning();
  },

  setStatusMessage(element, message, type = "info") {
    if (!element) return;
    element.textContent = message;
    element.className = "status-message";
    if (type === "error") element.classList.add("error-message");
    else if (type === "success") element.classList.add("success-message");
    else if (type === "loading") element.classList.add("loading-indicator");
    else element.classList.add("info-message");
    element.style.display = message ? "block" : "none";
  },
};

export default pinningUI;
