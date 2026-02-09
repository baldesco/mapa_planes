/**
 * addPlaceForm.js
 * Manages interactions and state for the Add New Place form.
 * Updated to support SPA-lite submission via API.
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
  onSuccessCallback: null,

  init(mapReady, showFn, hideFn, onSuccess) {
    this.isMapReady = mapReady;
    this.hideCallback = hideFn;
    this.onSuccessCallback = onSuccess;
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
    this.elements.displayAddress = document.getElementById("display-address");
    this.elements.hiddenLat = document.getElementById("latitude");
    this.elements.hiddenLon = document.getElementById("longitude");
    this.elements.hiddenAddress = document.getElementById("address");
    this.elements.hiddenCity = document.getElementById("city");
    this.elements.hiddenCountry = document.getElementById("country");
    this.elements.categorySelect = document.getElementById("add-category");
    this.elements.statusSelect = document.getElementById("add-status");
    this.elements.submitBtn = document.getElementById("add-place-submit-btn");
  },

  setupEventListeners() {
    if (!this.elements.form) return;

    this.elements.form.addEventListener("submit", (e) => this.handleSubmit(e));

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

  async handleSubmit(event) {
    event.preventDefault();

    this.setStatusMessage("Creating place...", "loading");
    this.elements.submitBtn.disabled = true;

    const payload = {
      name: this.elements.nameInput.value,
      latitude: parseFloat(this.elements.hiddenLat.value),
      longitude: parseFloat(this.elements.hiddenLon.value),
      category: this.elements.categorySelect.value,
      status: this.elements.statusSelect.value,
      address: this.elements.hiddenAddress.value || null,
      city: this.elements.hiddenCity.value || null,
      country: this.elements.hiddenCountry.value || null,
    };

    try {
      const response = await apiClient.post("/api/v1/places/", payload);
      if (response.ok) {
        const newPlace = await response.json();
        this.setStatusMessage("Place created successfully!", "success");
        if (this.onSuccessCallback) {
          this.onSuccessCallback(newPlace);
        }
        this.resetForm();
      } else {
        const error = await response.json();
        this.setStatusMessage(
          error.detail || "Failed to create place",
          "error",
        );
        this.elements.submitBtn.disabled = false;
      }
    } catch (error) {
      this.setStatusMessage("A network error occurred", "error");
      this.elements.submitBtn.disabled = false;
    }
  },

  resetForm() {
    if (this.elements.form) this.elements.form.reset();
    if (this.elements.coordsSection)
      this.elements.coordsSection.style.display = "none";
    this.setStatusMessage("");
    this.validateSubmitButton();
    pinningUI.deactivateIfActiveFor("add");
  },

  async handleGeocodeRequest() {
    const addressQuery = this.elements.addressInput?.value.trim();
    if (!addressQuery) {
      this.setStatusMessage("Please enter an address.", "error");
      return;
    }

    this.setStatusMessage("Searching...", "loading");
    try {
      const response = await apiClient.get(
        `/api/v1/geocode?address=${encodeURIComponent(addressQuery)}`,
      );
      if (response.ok) {
        const result = await response.json();
        this.updateCoordsDisplay(result);
        this.setStatusMessage(`Found: ${result.display_name}`, "success");
        mapHandler.flyTo(result.latitude, result.longitude);
      } else {
        this.setStatusMessage("Address not found.", "error");
      }
    } catch (error) {
      this.setStatusMessage("Geocoding service unavailable.", "error");
    }
  },

  updateCoordsDisplay(coordsData) {
    const els = this.elements;
    els.hiddenLat.value = coordsData.latitude;
    els.hiddenLon.value = coordsData.longitude;
    els.hiddenAddress.value = coordsData.address || "";
    els.hiddenCity.value = coordsData.city || "";
    els.hiddenCountry.value = coordsData.country || "";

    if (els.displayAddress) {
      els.displayAddress.textContent =
        coordsData.display_name ||
        `${coordsData.latitude.toFixed(4)}, ${coordsData.longitude.toFixed(4)}`;
    }

    els.coordsSection.style.display = "block";
    this.validateSubmitButton();
  },

  validateSubmitButton() {
    if (this.elements.submitBtn) {
      this.elements.submitBtn.disabled = !(
        this.elements.nameInput.value.trim() &&
        this.elements.hiddenLat.value &&
        this.elements.hiddenLon.value
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
