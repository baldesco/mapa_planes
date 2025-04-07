/**
 * addPlaceForm.js
 * Manages interactions and state for the Add New Place form.
 */
import apiClient from "../apiClient.js";
import mapHandler from "../mapHandler.js";
import pinningUI from "../components/pinningUI.js"; // Use the pinning UI module

const addPlaceForm = {
  elements: {
    form: null,
    wrapper: null,
    cancelBtn: null,
    nameInput: null,
    addressInput: null,
    findCoordsBtn: null,
    pinOnMapBtn: null,
    mapPinInstruction: null,
    geocodeStatus: null,
    coordsSection: null,
    displayLat: null,
    displayLon: null,
    displayAddress: null,
    hiddenLat: null,
    hiddenLon: null,
    hiddenAddress: null,
    hiddenCity: null,
    hiddenCountry: null,
    categorySelect: null,
    statusSelect: null,
    submitBtn: null,
  },
  isMapReady: false,
  hideCallback: null, // Function provided by orchestrator to hide this form

  init(mapReady, showFn, hideFn) {
    console.debug("Add Place Form: Initializing...");
    this.isMapReady = mapReady;
    this.hideCallback = hideFn; // Store the hide function
    this.cacheDOMElements();
    this.setupEventListeners();
    this.resetForm(); // Ensure clean state on init

    // Expose updateCoordsDisplay globally ONLY IF NEEDED by pinningUI/mapHandler directly
    // It's better if pinningUI calls a method *on this module*
    // window.updateAddFormCoords = this.updateCoordsDisplay.bind(this);
  },

  cacheDOMElements() {
    this.elements.wrapper = document.getElementById(
      "add-place-wrapper-section"
    );
    if (!this.elements.wrapper) return; // Stop if wrapper not found

    this.elements.form = document.getElementById("add-place-form");
    this.elements.cancelBtn = document.getElementById("add-place-cancel-btn");
    this.elements.nameInput = document.getElementById("name");
    this.elements.addressInput = document.getElementById("address-input");
    this.elements.findCoordsBtn = document.getElementById("find-coords-btn");
    this.elements.pinOnMapBtn = document.getElementById("pin-on-map-btn");
    this.elements.mapPinInstruction = document.getElementById(
      "map-pin-instruction"
    );
    this.elements.geocodeStatus = document.getElementById("geocode-status");
    this.elements.coordsSection = document.getElementById("coords-section");
    this.elements.displayLat = document.getElementById("display-lat");
    this.elements.displayLon = document.getElementById("display-lon");
    this.elements.displayAddress = document.getElementById("display-address");
    this.elements.hiddenLat = document.getElementById("latitude");
    this.elements.hiddenLon = document.getElementById("longitude");
    this.elements.hiddenAddress = document.getElementById("address");
    this.elements.hiddenCity = document.getElementById("city");
    this.elements.hiddenCountry = document.getElementById("country");
    this.elements.categorySelect = document.getElementById("add-category");
    this.elements.statusSelect = document.getElementById("add-status");
    this.elements.submitBtn = document.getElementById("add-place-submit-btn");

    // Disable map-dependent buttons if map isn't ready
    if (!this.isMapReady) {
      if (this.elements.findCoordsBtn)
        this.elements.findCoordsBtn.disabled = true; // Geocode relies on flyTo
      if (this.elements.pinOnMapBtn) this.elements.pinOnMapBtn.disabled = true;
    }
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
        // Call the pinningUI module to handle activation/deactivation
        pinningUI.togglePinning(
          "add",
          null,
          this.updateCoordsDisplay.bind(this)
        ); // Pass null coords, and callback
      });
    }

    // Form submission is handled by uiOrchestrator's setupFormSubmission
    // We might add specific validation hints here if needed
  },

  resetForm() {
    if (this.elements.form) this.elements.form.reset();
    if (this.elements.coordsSection)
      this.elements.coordsSection.style.display = "none";
    this.setStatusMessage(""); // Clear status
    // Clear hidden inputs
    if (this.elements.hiddenLat) this.elements.hiddenLat.value = "";
    if (this.elements.hiddenLon) this.elements.hiddenLon.value = "";
    if (this.elements.hiddenAddress) this.elements.hiddenAddress.value = "";
    if (this.elements.hiddenCity) this.elements.hiddenCity.value = "";
    if (this.elements.hiddenCountry) this.elements.hiddenCountry.value = "";
    // Clear display elements
    if (this.elements.displayLat) this.elements.displayLat.textContent = "";
    if (this.elements.displayLon) this.elements.displayLon.textContent = "";
    if (this.elements.displayAddress)
      this.elements.displayAddress.textContent = "";
    // Reset buttons
    if (this.elements.submitBtn) this.elements.submitBtn.disabled = true;
    if (this.elements.pinOnMapBtn)
      this.elements.pinOnMapBtn.textContent = "Pin Location on Map";
    if (this.elements.mapPinInstruction)
      this.elements.mapPinInstruction.style.display = "none";
    if (this.elements.addressInput) this.elements.addressInput.disabled = false;
    if (this.elements.findCoordsBtn)
      this.elements.findCoordsBtn.disabled = !this.isMapReady; // Re-enable based on map status

    // Ensure pinning UI associated with 'add' is reset if it was active
    pinningUI.deactivateIfActiveFor("add");
  },

  async handleGeocodeRequest() {
    pinningUI.deactivateIfActiveFor("add"); // Deactivate pinning if active

    const addressQuery = this.elements.addressInput?.value.trim();
    if (!addressQuery) {
      this.setStatusMessage("Please enter an address or place name.", "error");
      return;
    }

    this.setStatusMessage("Searching for location...", "loading");
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
          `Location found: ${result.display_name}`,
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
      console.error("Add Place Geocoding fetch error:", error);
      this.setStatusMessage(
        "Network error or server issue during geocoding.",
        "error"
      );
    } finally {
      if (this.elements.findCoordsBtn)
        this.elements.findCoordsBtn.disabled = false;
      // Re-enable submit only if coords are now valid
      if (
        this.elements.submitBtn &&
        this.elements.hiddenLat?.value &&
        this.elements.hiddenLon?.value
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
    if (
      !els.coordsSection ||
      !els.displayLat ||
      !els.displayLon ||
      !els.hiddenLat ||
      !els.hiddenLon ||
      !els.hiddenAddress ||
      !els.hiddenCity ||
      !els.hiddenCountry ||
      !els.submitBtn
    ) {
      console.error(
        "AddPlaceForm: Cannot update coords display, missing elements."
      );
      this.setStatusMessage("Internal UI Error updating coordinates.", "error");
      return;
    }

    const lat = parseFloat(coordsData.latitude);
    const lon = parseFloat(coordsData.longitude);

    if (isNaN(lat) || isNaN(lon)) {
      this.setStatusMessage("Received invalid coordinate data.", "error");
      els.submitBtn.disabled = true;
      els.hiddenLat.value = "";
      els.hiddenLon.value = "";
      els.displayLat.textContent = "N/A";
      els.displayLon.textContent = "N/A";
      if (els.displayAddress) els.displayAddress.textContent = "";
      els.coordsSection.style.display = "none";
      return;
    }

    els.hiddenLat.value = lat.toFixed(7);
    els.hiddenLon.value = lon.toFixed(7);

    // Update hidden address details only if provided (from geocoding)
    if (
      coordsData.address !== undefined ||
      coordsData.city !== undefined ||
      coordsData.country !== undefined ||
      coordsData.display_name !== undefined
    ) {
      els.hiddenAddress.value = coordsData.address || "";
      els.hiddenCity.value = coordsData.city || "";
      els.hiddenCountry.value = coordsData.country || "";
      if (els.displayAddress)
        els.displayAddress.textContent =
          coordsData.display_name || "(Coordinates set)";
    } else if (els.displayAddress) {
      // Only lat/lon provided (likely from pin), update display text
      els.displayAddress.textContent = "(Coordinates set via pin)";
      // Keep existing hidden address/city/country unless geocoding provides new ones
    }

    els.displayLat.textContent = lat.toFixed(6);
    els.displayLon.textContent = lon.toFixed(6);
    els.coordsSection.style.display = "block";
    els.submitBtn.disabled = false; // Enable submit
    console.log("AddPlaceForm: Coords updated", coordsData);
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

export default addPlaceForm;
