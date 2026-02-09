/**
 * editPlaceForm.js
 * Updated to ensure reliable UI state management.
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
    this.elements.cancelBtn?.addEventListener("click", () =>
      this.hideCallback(),
    );
    this.elements.findCoordsBtn?.addEventListener("click", () =>
      this.handleGeocodeRequest(),
    );
    this.elements.pinOnMapBtn?.addEventListener("click", () => {
      const coords = this.currentPlaceData
        ? {
            lat: this.currentPlaceData.latitude,
            lng: this.currentPlaceData.longitude,
          }
        : null;
      pinningUI.togglePinning("edit", coords, (c) =>
        this.updateCoordsDisplay(c),
      );
    });
  },

  populateForm(placeData) {
    if (!this.elements.form || !placeData) return false;
    this.currentPlaceData = placeData;
    const els = this.elements;
    els.formTitle.textContent = placeData.name;
    els.nameInput.value = placeData.name || "";
    els.categorySelect.value = placeData.category || "other";
    els.statusSelect.value = placeData.status || "pending";
    els.latitudeInput.value = placeData.latitude || "";
    els.longitudeInput.value = placeData.longitude || "";
    els.addressHidden.value = placeData.address || "";
    els.cityHidden.value = placeData.city || "";
    els.countryHidden.value = placeData.country || "";
    this.validateSubmitButton();
    return true;
  },

  async handleSubmit(event) {
    event.preventDefault();
    this.elements.submitBtn.disabled = true;
    const payload = {
      name: this.elements.nameInput.value,
      latitude: parseFloat(this.elements.latitudeInput.value),
      longitude: parseFloat(this.elements.longitudeInput.value),
      category: this.elements.categorySelect.value,
      status: this.elements.statusSelect.value,
      address: this.elements.addressHidden.value || null,
      city: this.elements.cityHidden.value || null,
      country: this.elements.countryHidden.value || null,
      tags: tagInput.getTags("edit-tags-input"),
    };
    try {
      const response = await apiClient.put(
        `/api/v1/places/${this.currentPlaceData.id}`,
        payload,
      );
      if (response.ok) {
        const updated = await response.json();
        this.onSuccessCallback(updated);
      } else {
        this.elements.submitBtn.disabled = false;
      }
    } catch (error) {
      this.elements.submitBtn.disabled = false;
    }
  },

  async handleGeocodeRequest() {
    const query = this.elements.addressInput?.value.trim();
    if (!query) return;
    try {
      const response = await apiClient.get(
        `/api/v1/geocode?address=${encodeURIComponent(query)}`,
      );
      if (response.ok) {
        const result = await response.json();
        this.updateCoordsDisplay(result);
        mapHandler.flyTo(result.latitude, result.longitude);
      }
    } catch (error) {}
  },

  updateCoordsDisplay(coordsData) {
    this.elements.latitudeInput.value = coordsData.latitude;
    this.elements.longitudeInput.value = coordsData.longitude;
    this.elements.addressHidden.value = coordsData.address || "";
    this.elements.cityHidden.value = coordsData.city || "";
    this.elements.countryHidden.value = coordsData.country || "";
    this.validateSubmitButton();
  },

  validateSubmitButton() {
    this.elements.submitBtn.disabled = !(
      this.elements.nameInput.value.trim() &&
      this.elements.latitudeInput.value &&
      this.elements.longitudeInput.value
    );
  },
};

export default editPlaceForm;
