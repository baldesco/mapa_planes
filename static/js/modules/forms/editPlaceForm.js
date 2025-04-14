/**
 * editPlaceForm.js
 * Manages interactions and state for the Edit Place form.
 * Tag input is handled externally by tagInput.js via uiOrchestrator.
 */
import apiClient from "../apiClient.js";
import mapHandler from "../mapHandler.js";
import pinningUI from "../components/pinningUI.js"; // Use the pinning UI module

const editPlaceForm = {
  elements: {
    form: null,
    wrapper: null,
    cancelBtn: null,
    formTitle: null,
    nameInput: null,
    addressInput: null,
    findCoordsBtn: null,
    pinOnMapBtn: null,
    mapPinInstruction: null,
    geocodeStatus: null,
    coordsSection: null,
    displayLat: null,
    displayLon: null,
    // Hidden inputs for actual submission
    latitudeInput: null,
    longitudeInput: null,
    addressHidden: null,
    cityHidden: null,
    countryHidden: null,
    categorySelect: null,
    statusSelect: null,
    tagsInputElement: null,
    submitBtn: null,
  },
  isMapReady: false,
  hideCallback: null, // Function provided by orchestrator to hide this form
  currentPlaceData: null, // Store data of the place being edited

  init(mapReady, showFn, hideFn) {
    console.debug("Edit Place Form: Initializing...");
    this.isMapReady = mapReady;
    this.hideCallback = hideFn;
    this.cacheDOMElements();
    this.setupEventListeners();

    // Disable map-dependent buttons if map isn't ready
    if (!this.isMapReady) {
      if (this.elements.findCoordsBtn)
        this.elements.findCoordsBtn.disabled = true;
      if (this.elements.pinOnMapBtn) this.elements.pinOnMapBtn.disabled = true;
    }
  },

  cacheDOMElements() {
    this.elements.wrapper = document.getElementById("edit-place-section");
    if (!this.elements.wrapper) return;

    this.elements.form = document.getElementById("edit-place-form");
    this.elements.cancelBtn =
      this.elements.wrapper.querySelector("button.cancel-btn");
    this.elements.formTitle = document.getElementById("edit-place-form-title");
    this.elements.nameInput = document.getElementById("edit-name");
    this.elements.addressInput = document.getElementById("edit-address-input");
    this.elements.findCoordsBtn = document.getElementById(
      "edit-find-coords-btn"
    );
    this.elements.pinOnMapBtn = document.getElementById("edit-pin-on-map-btn");
    this.elements.mapPinInstruction = document.getElementById(
      "edit-map-pin-instruction"
    );
    this.elements.geocodeStatus = document.getElementById(
      "edit-geocode-status"
    );
    this.elements.coordsSection = document.getElementById(
      "edit-coords-section"
    );
    this.elements.displayLat = document.getElementById("edit-display-lat");
    this.elements.displayLon = document.getElementById("edit-display-lon");
    this.elements.latitudeInput = document.getElementById("edit-latitude"); // Hidden input
    this.elements.longitudeInput = document.getElementById("edit-longitude"); // Hidden input
    this.elements.addressHidden = document.getElementById("edit-address"); // Hidden input
    this.elements.cityHidden = document.getElementById("edit-city"); // Hidden input
    this.elements.countryHidden = document.getElementById("edit-country"); // Hidden input
    this.elements.categorySelect = document.getElementById("edit-category");
    this.elements.statusSelect = document.getElementById("edit-status");
    // Get reference to the tag input element, but don't manipulate its value directly
    this.elements.tagsInputElement = document.getElementById("edit-tags-input");
    this.elements.submitBtn = document.getElementById("edit-place-submit-btn");
  },

  setupEventListeners() {
    if (!this.elements.form) return;

    if (this.elements.cancelBtn && this.hideCallback) {
      this.elements.cancelBtn.addEventListener("click", () =>
        this.hideCallback()
      );
    }

    if (this.elements.findCoordsBtn && this.isMapReady) {
      this.elements.findCoordsBtn.addEventListener("click", () =>
        this.handleGeocodeRequest()
      );
    }

    if (this.elements.pinOnMapBtn && this.isMapReady) {
      this.elements.pinOnMapBtn.addEventListener("click", () => {
        let initialCoords = null;
        if (this.currentPlaceData) {
          const lat = parseFloat(this.currentPlaceData.latitude);
          const lng = parseFloat(this.currentPlaceData.longitude);
          if (!isNaN(lat) && !isNaN(lng)) {
            initialCoords = { lat, lng };
          }
        }
        // Call the pinningUI module
        pinningUI.togglePinning(
          "edit",
          initialCoords,
          this.updateCoordsDisplay.bind(this)
        );
      });
    }
    // Form submission handled by uiOrchestrator
  },

  /** Populates the form with data for the place being edited */
  populateForm(placeData) {
    if (!this.elements.form) {
      console.error("Edit form elements not cached.");
      return false;
    }
    if (!placeData || typeof placeData !== "object") {
      console.error("Invalid placeData provided to populateForm:", placeData);
      return false;
    }

    this.currentPlaceData = placeData; // Store for later use (e.g., pinning)
    const els = this.elements;

    try {
      els.formTitle.textContent = `"${placeData.name || "Unknown"}"`;
      els.nameInput.value = placeData.name || "";
      els.categorySelect.value = placeData.category || "other";
      els.statusSelect.value = placeData.status || "pending";
      els.addressInput.value = ""; // Clear geocode input

      // Populate hidden inputs which hold the actual values
      els.latitudeInput.value = placeData.latitude || "";
      els.longitudeInput.value = placeData.longitude || "";
      els.addressHidden.value = placeData.address || "";
      els.cityHidden.value = placeData.city || "";
      els.countryHidden.value = placeData.country || "";

      // Update display elements
      els.displayLat.textContent = placeData.latitude?.toFixed(6) ?? "N/A";
      els.displayLon.textContent = placeData.longitude?.toFixed(6) ?? "N/A";
      els.coordsSection.style.display =
        placeData.latitude && placeData.longitude ? "block" : "none";

      // Reset status and buttons
      this.setStatusMessage("");
      els.submitBtn.disabled = !(
        els.latitudeInput.value && els.longitudeInput.value
      );
      els.submitBtn.textContent = "Save Changes";
      els.form.action = `/places/${placeData.id}/edit`; // Set correct action URL
      els.pinOnMapBtn.textContent = "Pin New Location";
      els.mapPinInstruction.style.display = "none";
      els.addressInput.disabled = false;
      els.findCoordsBtn.disabled = !this.isMapReady;
      els.pinOnMapBtn.disabled = !this.isMapReady;

      return true; // Indicate success
    } catch (e) {
      console.error("Error populating edit form fields:", e);
      this.currentPlaceData = null; // Clear data on error
      return false; // Indicate failure
    }
  },

  async handleGeocodeRequest() {
    pinningUI.deactivateIfActiveFor("edit"); // Deactivate pinning if active

    const addressQuery = this.elements.addressInput?.value.trim();
    if (!addressQuery) {
      this.setStatusMessage(
        "Please enter an address or place name to find new coordinates.",
        "error"
      );
      return;
    }

    this.setStatusMessage("Searching for new location...", "loading");
    if (this.elements.findCoordsBtn)
      this.elements.findCoordsBtn.disabled = true;
    if (this.elements.submitBtn) this.elements.submitBtn.disabled = true;

    try {
      const geocodeUrl = `/api/v1/geocode?address=${encodeURIComponent(
        addressQuery
      )}`;
      const response = await apiClient.get(geocodeUrl);

      if (response.ok) {
        const result = await response.json();
        this.updateCoordsDisplay(result); // Update this form's display
        this.setStatusMessage(
          `New location found: ${result.display_name}`,
          "success"
        );
        mapHandler.flyTo(result.latitude, result.longitude); // Fly main map
      } else {
        let errorDetail = `Geocoding failed (${response.status}).`;
        try {
          const errorData = await response.json();
          errorDetail = errorData.detail || errorDetail;
        } catch (e) {
          /* ignore */
        }
        this.setStatusMessage(`Error: ${errorDetail}`, "error");
      }
    } catch (error) {
      console.error("Edit Place Geocoding fetch error:", error);
      this.setStatusMessage(
        "Network error or server issue during geocoding.",
        "error"
      );
    } finally {
      if (this.elements.findCoordsBtn)
        this.elements.findCoordsBtn.disabled = false;
      // Re-enable submit only if coords are valid
      if (
        this.elements.submitBtn &&
        this.elements.latitudeInput?.value &&
        this.elements.longitudeInput?.value
      ) {
        this.elements.submitBtn.disabled = false;
      } else if (this.elements.submitBtn) {
        this.elements.submitBtn.disabled = true;
      }
    }
  },

  /** Updates the coordinate display and hidden inputs for THIS form */
  updateCoordsDisplay(coordsData) {
    const els = this.elements;
    // Ensure all required elements exist
    if (
      !els.coordsSection ||
      !els.displayLat ||
      !els.displayLon ||
      !els.latitudeInput ||
      !els.longitudeInput ||
      !els.addressHidden ||
      !els.cityHidden ||
      !els.countryHidden ||
      !els.submitBtn
    ) {
      console.error(
        "EditPlaceForm: Cannot update coords display, missing elements."
      );
      this.setStatusMessage("Internal UI Error updating coordinates.", "error");
      return;
    }

    const lat = parseFloat(coordsData.latitude);
    const lon = parseFloat(coordsData.longitude);

    if (isNaN(lat) || isNaN(lon)) {
      this.setStatusMessage("Received invalid coordinate data.", "error");
      els.submitBtn.disabled = true;
      els.latitudeInput.value = "";
      els.longitudeInput.value = ""; // Clear hidden inputs
      els.displayLat.textContent = "N/A";
      els.displayLon.textContent = "N/A";
      els.coordsSection.style.display = "none";
      return;
    }

    // Update hidden inputs (these are submitted)
    els.latitudeInput.value = lat.toFixed(7);
    els.longitudeInput.value = lon.toFixed(7);

    // Update hidden address details only if provided (from geocoding)
    if (
      coordsData.address !== undefined ||
      coordsData.city !== undefined ||
      coordsData.country !== undefined ||
      coordsData.display_name !== undefined
    ) {
      els.addressHidden.value = coordsData.address || "";
      els.cityHidden.value = coordsData.city || "";
      els.countryHidden.value = coordsData.country || "";
    }

    // Update display elements
    els.displayLat.textContent = lat.toFixed(6);
    els.displayLon.textContent = lon.toFixed(6);
    els.coordsSection.style.display = "block";
    els.submitBtn.disabled = false; // Enable submit
    console.log("EditPlaceForm: Coords updated", coordsData);
  },

  setStatusMessage(message, type = "info") {
    const element = this.elements.geocodeStatus;
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

export default editPlaceForm;
