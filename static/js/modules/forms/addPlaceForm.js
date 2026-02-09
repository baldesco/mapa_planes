/**
 * addPlaceForm.js
 * Manages interactions and state for the Add New Place form.
 * Coordinates with mapHandler and pinningUI for location selection.
 */
import apiClient from "../apiClient.js";
import mapHandler from "../mapHandler.js";
import pinningUI from "../components/pinningUI.js";

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
  hideCallback: null,

  init(mapReady, showFn, hideFn) {
    this.isMapReady = mapReady;
    this.hideCallback = hideFn;
    this.cacheDOMElements();
    this.setupEventListeners();
    this.resetForm();
  },

  cacheDOMElements() {
    this.elements.wrapper = document.getElementById(
      "add-place-wrapper-section",
    );
    if (!this.elements.wrapper) return;

    this.elements.form = document.getElementById("add-place-form");
    this.elements.cancelBtn = document.getElementById("add-place-cancel-btn");
    this.elements.nameInput = document.getElementById("name");
    this.elements.addressInput = document.getElementById("address-input");
    this.elements.findCoordsBtn = document.getElementById("find-coords-btn");
    this.elements.pinOnMapBtn = document.getElementById("pin-on-map-btn");
    this.elements.mapPinInstruction = document.getElementById(
      "map-pin-instruction",
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

    if (!this.isMapReady) {
      if (this.elements.findCoordsBtn)
        this.elements.findCoordsBtn.disabled = true;
      if (this.elements.pinOnMapBtn) this.elements.pinOnMapBtn.disabled = true;
    }
  },

  setupEventListeners() {
    if (!this.elements.form) return;

    if (this.elements.cancelBtn && this.hideCallback) {
      this.elements.cancelBtn.addEventListener("click", () =>
        this.hideCallback(),
      );
    }

    if (this.elements.findCoordsBtn && this.isMapReady) {
      this.elements.findCoordsBtn.addEventListener("click", () =>
        this.handleGeocodeRequest(),
      );
    }

    if (this.elements.pinOnMapBtn && this.isMapReady) {
      this.elements.pinOnMapBtn.addEventListener("click", () => {
        pinningUI.togglePinning(
          "add",
          null,
          this.updateCoordsDisplay.bind(this),
        );
      });
    }
  },

  resetForm() {
    if (this.elements.form) this.elements.form.reset();
    if (this.elements.coordsSection)
      this.elements.coordsSection.style.display = "none";
    this.setStatusMessage("");

    const hiddenFields = [
      "hiddenLat",
      "hiddenLon",
      "hiddenAddress",
      "hiddenCity",
      "hiddenCountry",
    ];
    hiddenFields.forEach((field) => {
      if (this.elements[field]) this.elements[field].value = "";
    });

    const displayFields = ["displayLat", "displayLon", "displayAddress"];
    displayFields.forEach((field) => {
      if (this.elements[field]) this.elements[field].textContent = "";
    });

    if (this.elements.submitBtn) this.elements.submitBtn.disabled = true;
    if (this.elements.pinOnMapBtn)
      this.elements.pinOnMapBtn.textContent = "Pin Location on Map";
    if (this.elements.mapPinInstruction)
      this.elements.mapPinInstruction.style.display = "none";
    if (this.elements.addressInput) this.elements.addressInput.disabled = false;
    if (this.elements.findCoordsBtn)
      this.elements.findCoordsBtn.disabled = !this.isMapReady;

    pinningUI.deactivateIfActiveFor("add");
  },

  async handleGeocodeRequest() {
    pinningUI.deactivateIfActiveFor("add");

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
      const geocodeUrl = `/api/v1/geocode?address=${encodeURIComponent(addressQuery)}`;
      const response = await apiClient.get(geocodeUrl);

      if (response.ok) {
        const result = await response.json();
        this.updateCoordsDisplay(result);
        this.setStatusMessage(
          `Location found: ${result.display_name}`,
          "success",
        );
        mapHandler.flyTo(result.latitude, result.longitude);
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
      this.setStatusMessage("Network error during geocoding.", "error");
    } finally {
      if (this.elements.findCoordsBtn)
        this.elements.findCoordsBtn.disabled = false;
      this.validateSubmitButton();
    }
  },

  updateCoordsDisplay(coordsData) {
    const els = this.elements;
    const lat = parseFloat(coordsData.latitude);
    const lon = parseFloat(coordsData.longitude);

    if (isNaN(lat) || isNaN(lon)) {
      this.setStatusMessage("Invalid coordinate data.", "error");
      return;
    }

    els.hiddenLat.value = lat.toFixed(7);
    els.hiddenLon.value = lon.toFixed(7);

    if (coordsData.display_name) {
      els.hiddenAddress.value = coordsData.address || "";
      els.hiddenCity.value = coordsData.city || "";
      els.hiddenCountry.value = coordsData.country || "";
      if (els.displayAddress)
        els.displayAddress.textContent = coordsData.display_name;
    } else if (els.displayAddress) {
      els.displayAddress.textContent = "(Coordinates set via pin)";
    }

    els.displayLat.textContent = lat.toFixed(6);
    els.displayLon.textContent = lon.toFixed(6);
    els.coordsSection.style.display = "block";
    this.validateSubmitButton();
  },

  validateSubmitButton() {
    if (this.elements.submitBtn) {
      this.elements.submitBtn.disabled = !(
        this.elements.hiddenLat?.value && this.elements.hiddenLon?.value
      );
    }
  },

  setStatusMessage(message, type = "info") {
    const element = this.elements.geocodeStatus;
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

export default addPlaceForm;
