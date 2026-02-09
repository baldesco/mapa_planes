/**
 * pinningUI.js
 * Manages the UI state for the map pinning feature.
 * Uses the fixed overlay container for a consistent user experience.
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
  },
  isActive: false,
  activeFormType: null,
  updateCoordsCallback: null,
  isMapReady: false,

  init(mapReadyStatus) {
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
  },

  setupEventListeners() {
    this.elements.confirmBtn?.addEventListener("click", () =>
      this.confirmPinLocation(),
    );
    this.elements.cancelBtn?.addEventListener("click", () =>
      this.deactivatePinning(),
    );
  },

  /**
   * Toggles pinning mode.
   * @param {string} formType - 'add' or 'edit'
   * @param {object} initialCoords - {lat, lng} or null
   * @param {function} updateCallback - Function to call with new coords
   */
  togglePinning(formType, initialCoords, updateCallback) {
    if (!this.isMapReady) return;

    if (this.isActive && this.activeFormType === formType) {
      this.deactivatePinning();
    } else {
      this.activatePinning(formType, initialCoords, updateCallback);
    }
  },

  activatePinning(formType, initialCoords, updateCallback) {
    this.isActive = true;
    this.activeFormType = formType;
    this.updateCoordsCallback = updateCallback;

    const container = this.elements.mapContainer;
    if (!container) return;

    container.style.display = "flex";

    if (mapHandler.initPinningMap("pinning-map", initialCoords)) {
      mapHandler.placeDraggableMarker(initialCoords);
      this.updateFormUI(true, formType);
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

    this.updateFormUI(false, formType);
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

    if (isActive) {
      if (instructionEl) instructionEl.style.display = "block";
      if (pinBtn) pinBtn.textContent = "Cancel Pinning";
    } else {
      if (instructionEl) instructionEl.style.display = "none";
      if (pinBtn)
        pinBtn.textContent = isEdit ? "Pin New Location" : "Pin on Map";
    }
  },

  confirmPinLocation() {
    if (!this.isActive || !this.updateCoordsCallback) return;

    const position = mapHandler.getDraggableMarkerPosition();
    if (position) {
      this.updateCoordsCallback({
        latitude: position.lat,
        longitude: position.lng,
      });
    }
    this.deactivatePinning();
  },
};

export default pinningUI;
