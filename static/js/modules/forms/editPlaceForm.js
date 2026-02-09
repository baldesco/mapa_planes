/**
 * editPlaceForm.js
 * Manages interactions and state for the Edit Place form.
 * Updated to support SPA-lite submission via API.
 */
import apiClient from "../apiClient.js";
import mapHandler from "../mapHandler.js";
import pinningUI from "../components/pinningUI.js";
import tagInput from "../components/tagInput.js";

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
    geocodeStatus: null,
    coordsSection: null,
    displayLat: null,
    displayLon: null,
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
  hideCallback: null,
  onSuccessCallback: null,
  currentPlaceData: null,

  init(mapReady, showFn, hideFn, onSuccess) {
    this.isMapReady = mapReady;
    this.hideCallback = hideFn;
    this.onSuccessCallback = onSuccess;
    this.cacheDOMElements();
    this.setupEventListeners();
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
      "edit-find-coords-btn",
    );
    this.elements.pinOnMapBtn = document.getElementById("edit-pin-on-map-btn");
    this.elements.geocodeStatus = document.getElementById(
      "edit-geocode-status",
    );
    this.elements.coordsSection = document.getElementById(
      "edit-coords-section",
    );
    this.elements.displayLat = document.getElementById("edit-display-lat");
    this.elements.displayLon = document.getElementById("edit-display-lon");
    this.elements.latitudeInput = document.getElementById("edit-latitude");
    this.elements.longitudeInput = document.getElementById("edit-longitude");
    this.elements.addressHidden = document.getElementById("edit-address");
    this.elements.cityHidden = document.getElementById("edit-city");
    this.elements.countryHidden = document.getElementById("edit-country");
    this.elements.categorySelect = document.getElementById("edit-category");
    this.elements.statusSelect = document.getElementById("edit-status");
    this.elements.tagsInputElement = document.getElementById("edit-tags-input");
    this.elements.submitBtn = document.getElementById("edit-place-submit-btn");
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
        let initialCoords = null;
        if (
          this.currentPlaceData?.latitude &&
          this.currentPlaceData?.longitude
        ) {
          initialCoords = {
            lat: this.currentPlaceData.latitude,
            lng: this.currentPlaceData.longitude,
          };
        }
        pinningUI.togglePinning(
          "edit",
          initialCoords,
          this.updateCoordsDisplay.bind(this),
        );
      });
    }
  },

  populateForm(placeData) {
    if (!this.elements.form || !placeData) return false;

    this.currentPlaceData = placeData;
    const els = this.elements;

    els.formTitle.textContent = placeData.name || "Unknown";
    els.nameInput.value = placeData.name || "";
    els.categorySelect.value = placeData.category || "other";
    els.statusSelect.value = placeData.status || "pending";
    els.addressInput.value = "";

    els.latitudeInput.value = placeData.latitude || "";
    els.longitudeInput.value = placeData.longitude || "";
    els.addressHidden.value = placeData.address || "";
    els.cityHidden.value = placeData.city || "";
    els.countryHidden.value = placeData.country || "";

    els.displayLat.textContent = placeData.latitude?.toFixed(6) ?? "N/A";
    els.displayLon.textContent = placeData.longitude?.toFixed(6) ?? "N/A";

    this.setStatusMessage("");
    this.validateSubmitButton();

    return true;
  },

  async handleSubmit(event) {
    event.preventDefault();
    if (!this.currentPlaceData) return;

    this.setStatusMessage("Updating place...", "loading");
    this.elements.submitBtn.disabled = true;

    const tags = tagInput.getTags("edit-tags-input");

    const payload = {
      name: this.elements.nameInput.value,
      latitude: parseFloat(this.elements.latitudeInput.value),
      longitude: parseFloat(this.elements.longitudeInput.value),
      category: this.elements.categorySelect.value,
      status: this.elements.statusSelect.value,
      address: this.elements.addressHidden.value || null,
      city: this.elements.cityHidden.value || null,
      country: this.elements.countryHidden.value || null,
      tags: tags,
    };

    try {
      const response = await apiClient.put(
        `/api/v1/places/${this.currentPlaceData.id}`,
        payload,
      );
      if (response.ok) {
        const updatedPlace = await response.json();
        this.setStatusMessage("Place updated successfully!", "success");
        if (this.onSuccessCallback) {
          this.onSuccessCallback(updatedPlace);
        }
      } else {
        const error = await response.json();
        this.setStatusMessage(error.detail || "Update failed", "error");
        this.elements.submitBtn.disabled = false;
      }
    } catch (error) {
      this.setStatusMessage("A network error occurred", "error");
      this.elements.submitBtn.disabled = false;
    }
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
    els.latitudeInput.value = coordsData.latitude;
    els.longitudeInput.value = coordsData.longitude;
    els.addressHidden.value = coordsData.address || "";
    els.cityHidden.value = coordsData.city || "";
    els.countryHidden.value = coordsData.country || "";

    els.displayLat.textContent = coordsData.latitude.toFixed(6);
    els.displayLon.textContent = coordsData.longitude.toFixed(6);

    this.validateSubmitButton();
  },

  validateSubmitButton() {
    if (this.elements.submitBtn) {
      this.elements.submitBtn.disabled = !(
        this.elements.nameInput.value.trim() &&
        this.elements.latitudeInput.value &&
        this.elements.longitudeInput.value
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

export default editPlaceForm;
