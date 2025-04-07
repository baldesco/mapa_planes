/**
 * pinningUI.js
 * Manages the UI state and interactions for the map pinning feature,
 * coordinating with mapHandler.js for map operations.
 */
import mapHandler from "../mapHandler.js";

const pinningUI = {
  elements: {
    // Buttons from both forms
    addPinBtn: null,
    editPinBtn: null,
    // Instructions from both forms
    addInstruction: null,
    editInstruction: null,
    // Pinning map container and controls
    mapContainer: null,
    confirmBtn: null,
    cancelBtn: null,
    // Status elements from both forms
    addStatus: null,
    editStatus: null,
  },
  isActive: false,
  activeFormType: null, // 'add' or 'edit'
  updateCoordsCallback: null, // Function to call on the form module to update its coords
  isMapReady: false,

  init(mapReadyStatus) {
    console.debug("Pinning UI: Initializing...");
    this.isMapReady = mapReadyStatus;
    this.cacheDOMElements();
    // *** ADD EVENT LISTENERS FOR SHARED BUTTONS HERE ***
    this.setupEventListeners();
  },

  cacheDOMElements() {
    this.elements.addPinBtn = document.getElementById("pin-on-map-btn");
    this.elements.editPinBtn = document.getElementById("edit-pin-on-map-btn");
    this.elements.addInstruction = document.getElementById(
      "map-pin-instruction"
    );
    this.elements.editInstruction = document.getElementById(
      "edit-map-pin-instruction"
    );
    this.elements.mapContainer = document.getElementById(
      "pinning-map-container"
    );
    this.elements.confirmBtn = document.getElementById("confirm-pin-btn");
    this.elements.cancelBtn = document.getElementById("cancel-pin-btn");
    this.elements.addStatus = document.getElementById("geocode-status");
    this.elements.editStatus = document.getElementById("edit-geocode-status");
  },

  // *** NEW: Setup listeners for confirm/cancel ***
  setupEventListeners() {
    if (this.elements.confirmBtn) {
      this.elements.confirmBtn.addEventListener("click", () =>
        this.confirmPinLocation()
      );
    }
    if (this.elements.cancelBtn) {
      this.elements.cancelBtn.addEventListener("click", () => {
        // Cancel just deactivates the current mode
        if (this.isActive && this.activeFormType) {
          this.togglePinning(this.activeFormType, null, null); // Call toggle to turn off
        }
      });
    }
  },

  /**
   * Toggles the pinning mode on or off for a specific form.
   * @param {'add'|'edit'} formType - The type of form activating pinning.
   * @param {object|null} initialCoords - Optional {lat, lng} for initial position.
   * @param {function} updateCallback - Function on the calling form module to update its coords.
   */
  togglePinning(formType, initialCoords, updateCallback) {
    console.log(
      `Pinning UI: togglePinning called for ${formType}. Currently active: ${
        this.isActive ? this.activeFormType : "none"
      }`
    );
    if (!this.isMapReady) {
      alert("Map functionality is not available. Cannot use pin feature.");
      console.warn("Pinning attempt failed: Map not ready.");
      return;
    }
    if (typeof L === "undefined") {
      alert("Mapping library (Leaflet) is not loaded. Cannot use pin feature.");
      console.error("Toggle Pinning failed: Leaflet (L) is undefined.");
      return;
    }

    if (this.isActive && this.activeFormType === formType) {
      // Turn OFF
      console.log(`Pinning UI: Turning OFF pinning for ${formType}`);
      this.deactivatePinning(); // Use the dedicated deactivate function
    } else {
      // Turn ON
      console.log(`Pinning UI: Turning ON pinning for ${formType}`);
      // Deactivate any existing pinning first (for the other form)
      if (this.isActive) {
        this.deactivatePinning();
      }
      // Activate for the new form
      this.activatePinning(formType, initialCoords, updateCallback);
    }
  },

  /** Activates the pinning mode */
  activatePinning(formType, initialCoords, updateCallback) {
    console.log(`Pinning UI: Activating for ${formType}`);
    this.isActive = true;
    this.activeFormType = formType;
    this.updateCoordsCallback = updateCallback;

    const container = this.elements.mapContainer;
    if (!container) {
      console.error("Pinning map container not found!");
      this.isActive = false;
      this.activeFormType = null;
      return;
    }

    this.moveMapContainer(formType); // Ensure container is in the right place
    container.style.display = "block";

    if (mapHandler.initPinningMap("pinning-map", initialCoords)) {
      mapHandler.placeDraggableMarker(initialCoords);
      this.updateFormUI(true, formType);
      container.scrollIntoView({ behavior: "smooth", block: "nearest" });
    } else {
      alert("Failed to initialize pinning map.");
      this.deactivatePinning(); // Clean up on failure
    }
  },

  /** Deactivates the pinning mode */
  deactivatePinning() {
    if (!this.isActive) return;
    console.log(`Pinning UI: Deactivating for ${this.activeFormType}`);
    const formType = this.activeFormType; // Store before clearing
    this.isActive = false;
    this.activeFormType = null;
    this.updateCoordsCallback = null;

    mapHandler.destroyPinningMap();
    if (this.elements.mapContainer) {
      this.elements.mapContainer.style.display = "none";
    }
    // Update UI for the form that *was* active
    if (formType) {
      this.updateFormUI(false, formType);
    }
  },

  /** Deactivates pinning only if it was active for the specified form type */
  deactivateIfActiveFor(formType) {
    if (this.isActive && this.activeFormType === formType) {
      this.deactivatePinning();
    }
  },

  /** Updates the UI elements of the specified form based on pinning state */
  updateFormUI(isActive, formType) {
    const isEdit = formType === "edit";
    const pinBtn = isEdit ? this.elements.editPinBtn : this.elements.addPinBtn;
    const instructionEl = isEdit
      ? this.elements.editInstruction
      : this.elements.addInstruction;
    const addressInput = isEdit
      ? this.elements.editAddressInput
      : this.elements.addAddressInput;
    const findBtn = isEdit
      ? this.elements.editFindCoordsBtn
      : this.elements.addFindCoordsBtn;
    const statusEl = isEdit
      ? this.elements.editStatus
      : this.elements.addStatus;

    // Check if elements exist before trying to modify them
    if (!pinBtn || !instructionEl || !addressInput || !findBtn || !statusEl) {
      console.warn(
        `updateFormUI: Could not find all required UI elements for form type ${formType}. Some UI updates might be skipped.`
      );
      // Attempt to update the elements that *were* found
    }

    if (isActive) {
      if (addressInput) addressInput.disabled = true;
      if (findBtn) findBtn.disabled = true;
      if (instructionEl) instructionEl.style.display = "block";
      if (pinBtn) pinBtn.textContent = "Cancel Pinning";
      this.setStatusMessage(
        statusEl,
        "Drag the pin on the map, then confirm.",
        "info"
      );
    } else {
      if (addressInput) addressInput.disabled = false;
      if (findBtn) findBtn.disabled = !this.isMapReady; // Re-enable based on map status
      if (instructionEl) instructionEl.style.display = "none";
      if (pinBtn)
        pinBtn.textContent = isEdit
          ? "Pin New Location"
          : "Pin Location on Map";

      // Reset submit button state based on current coords validity
      const latInput = isEdit
        ? document.getElementById("edit-latitude")
        : document.getElementById("latitude");
      const lonInput = isEdit
        ? document.getElementById("edit-longitude")
        : document.getElementById("longitude");
      const submitBtn = isEdit
        ? document.getElementById("edit-place-submit-btn")
        : document.getElementById("add-place-submit-btn");
      if (submitBtn && latInput && lonInput) {
        submitBtn.disabled = !(latInput.value && lonInput.value);
      } else if (submitBtn) {
        submitBtn.disabled = true; // Disable if inputs not found
      }
    }
    console.log(
      `handlePinningModeChange: Set UI for ${
        isActive ? "active" : "inactive"
      } pinning (${formType})`
    );
  },

  /** Moves the map container to the appropriate form */
  moveMapContainer(formType) {
    const container = this.elements.mapContainer;
    const targetFormSection =
      formType === "edit"
        ? this.elements.editPlaceSection
        : this.elements.addPlaceWrapper;
    const pinInstructionElement =
      formType === "edit"
        ? this.elements.editInstruction
        : this.elements.addInstruction;

    if (
      container &&
      targetFormSection &&
      pinInstructionElement &&
      targetFormSection.contains(pinInstructionElement)
    ) {
      pinInstructionElement.parentNode.insertBefore(
        container,
        pinInstructionElement.nextSibling
      );
      console.log(`Moved pinning map container into ${formType} form section.`);
    } else {
      console.error(
        `Could not find target section or instruction element for ${formType} to insert map container.`
      );
    }
  },

  /** Handles the confirm button click */
  confirmPinLocation() {
    if (!this.isActive || !this.activeFormType || !this.updateCoordsCallback) {
      console.warn(
        "Confirm pin clicked but pinning is not active or callback missing."
      );
      return;
    }
    const position = mapHandler.getDraggableMarkerPosition();
    const formType = this.activeFormType; // Get before deactivating
    const statusEl =
      formType === "edit" ? this.elements.editStatus : this.elements.addStatus;

    if (position) {
      const coords = { latitude: position.lat, longitude: position.lng };
      try {
        this.updateCoordsCallback(coords); // Call the form's update function
        this.setStatusMessage(statusEl, "Location set via map pin.", "success");
      } catch (e) {
        console.error("Error executing updateCoordsCallback:", e);
        this.setStatusMessage(
          statusEl,
          "Error updating form coordinates.",
          "error"
        );
      }
    } else {
      console.error("Could not get marker position on confirm.");
      this.setStatusMessage(statusEl, "Error getting pin location.", "error");
    }
    this.deactivatePinning(); // Deactivate pinning after confirm/error
  },

  /** Sets status message on the correct form's status element */
  setStatusMessage(element, message, type = "info") {
    if (!element) return;
    element.textContent = message;
    element.className = "status-message"; // Reset classes
    if (type === "error") element.classList.add("error-message");
    else if (type === "success") element.classList.add("success-message");
    else if (type === "loading") element.classList.add("loading-indicator");
    else element.classList.add("info-message");
    element.style.display = message ? "block" : "none";
  },
};

export default pinningUI;
