/**
 * ui.js
 * Module for handling general UI interactions, form display, DOM updates,
 * modals, rating stars, geocoding requests, and draggable map pinning
 * using a dedicated pinning map instance.
 */
import apiClient from "./apiClient.js";
import mapHandler from "./mapHandler.js";

const ui = {
  elements: {
    /* ... same elements ... */
    toggleAddPlaceBtn: null,
    addPlaceWrapper: null,
    addPlaceForm: null,
    addPlaceCancelBtn: null,
    addAddressInput: null,
    addFindCoordsBtn: null,
    addGeocodeStatus: null,
    addCoordsSection: null,
    addDisplayLat: null,
    addDisplayLon: null,
    addDisplayAddress: null,
    addHiddenLat: null,
    addHiddenLon: null,
    addHiddenAddress: null,
    addHiddenCity: null,
    addHiddenCountry: null,
    addSubmitBtn: null,
    addNameInput: null,
    addCategorySelect: null,
    addStatusSelect: null,
    addPinOnMapBtn: null,
    addMapPinInstruction: null,
    editPlaceSection: null,
    editPlaceForm: null,
    editPlaceFormTitle: null,
    editNameInput: null,
    editAddressInput: null,
    editFindCoordsBtn: null,
    editGeocodeStatus: null,
    editCoordsSection: null,
    editDisplayLat: null,
    editDisplayLon: null,
    editLatitudeInput: null,
    editLongitudeInput: null,
    editAddressHidden: null,
    editCityHidden: null,
    editCountryHidden: null,
    editCategorySelect: null,
    editStatusSelect: null,
    editSubmitBtn: null,
    editPinOnMapBtn: null,
    editMapPinInstruction: null,
    editCancelBtn: null,
    reviewImageSection: null,
    reviewImageForm: null,
    reviewFormTitle: null,
    reviewTitleInput: null,
    reviewTextInput: null,
    reviewRatingStarsContainer: null,
    reviewRatingInput: null,
    reviewImageInput: null,
    reviewRemoveImageCheckbox: null,
    currentImageReviewSection: null,
    currentImageReviewThumb: null,
    reviewSubmitBtn: null,
    reviewCancelBtn: null,
    seeReviewSection: null,
    seeReviewPlaceTitle: null,
    seeReviewRatingDisplay: null,
    seeReviewDisplayTitle: null,
    seeReviewDisplayText: null,
    seeReviewDisplayImage: null,
    seeReviewEditBtn: null,
    seeReviewCloseBtn: null,
    pinningMapContainer: null,
    pinningMapDiv: null,
    pinningMapControls: null,
    confirmPinBtn: null,
    cancelPinBtn: null,
  },
  currentPlaceDataForEdit: null,
  currentPlaceDataForReview: null,
  pinningActiveForForm: null, // State: null, 'add', or 'edit'

  init() {
    /* ... same ... */
    console.debug("UI Module: Initializing...");
    this.cacheDOMElements();
    this.setupEventListeners();
    this.setupRatingStars();
    window.showAddPlaceForm = this.showAddPlaceForm.bind(this);
    window.hideAddPlaceForm = this.hideAddPlaceForm.bind(this);
    window.showEditPlaceForm = this.showEditPlaceForm.bind(this);
    window.showReviewForm = this.showReviewForm.bind(this);
    window.showSeeReviewModal = this.showSeeReviewModal.bind(this);
    window.showImageOverlay = this.showImageOverlay.bind(this);
    window.ui = this;
    this.hideAllSections();
    if (this.elements.addSubmitBtn) this.elements.addSubmitBtn.disabled = true;
    if (this.elements.editSubmitBtn)
      this.elements.editSubmitBtn.disabled = true;
    if (this.elements.addPinOnMapBtn)
      this.elements.addPinOnMapBtn.disabled = false;
    if (this.elements.editPinOnMapBtn)
      this.elements.editPinOnMapBtn.disabled = false;
    console.log("UI Module: Initialization Complete.");
  },
  cacheDOMElements() {
    /* ... same ... */
    this.elements.toggleAddPlaceBtn = document.getElementById(
      "toggle-add-place-form-btn"
    );
    this.elements.addPlaceWrapper = document.getElementById(
      "add-place-wrapper-section"
    );
    this.elements.addPlaceForm = document.getElementById("add-place-form");
    this.elements.addPlaceCancelBtn = document.getElementById(
      "add-place-cancel-btn"
    );
    this.elements.addAddressInput = document.getElementById("address-input");
    this.elements.addFindCoordsBtn = document.getElementById("find-coords-btn");
    this.elements.addGeocodeStatus = document.getElementById("geocode-status");
    this.elements.addCoordsSection = document.getElementById("coords-section");
    this.elements.addDisplayLat = document.getElementById("display-lat");
    this.elements.addDisplayLon = document.getElementById("display-lon");
    this.elements.addDisplayAddress =
      document.getElementById("display-address");
    this.elements.addHiddenLat = document.getElementById("latitude");
    this.elements.addHiddenLon = document.getElementById("longitude");
    this.elements.addHiddenAddress = document.getElementById("address");
    this.elements.addHiddenCity = document.getElementById("city");
    this.elements.addHiddenCountry = document.getElementById("country");
    this.elements.addSubmitBtn = document.getElementById(
      "add-place-submit-btn"
    );
    this.elements.addNameInput = document.getElementById("name");
    this.elements.addCategorySelect = document.getElementById("add-category");
    this.elements.addStatusSelect = document.getElementById("add-status");
    this.elements.addPinOnMapBtn = document.getElementById("pin-on-map-btn");
    this.elements.addMapPinInstruction = document.getElementById(
      "map-pin-instruction"
    );
    this.elements.editPlaceSection =
      document.getElementById("edit-place-section");
    this.elements.editPlaceForm = document.getElementById("edit-place-form");
    this.elements.editPlaceFormTitle = document.getElementById(
      "edit-place-form-title"
    );
    this.elements.editNameInput = document.getElementById("edit-name");
    this.elements.editAddressInput =
      document.getElementById("edit-address-input");
    this.elements.editFindCoordsBtn = document.getElementById(
      "edit-find-coords-btn"
    );
    this.elements.editGeocodeStatus = document.getElementById(
      "edit-geocode-status"
    );
    this.elements.editCoordsSection = document.getElementById(
      "edit-coords-section"
    );
    this.elements.editDisplayLat = document.getElementById("edit-display-lat");
    this.elements.editDisplayLon = document.getElementById("edit-display-lon");
    this.elements.editLatitudeInput = document.getElementById("edit-latitude");
    this.elements.editLongitudeInput =
      document.getElementById("edit-longitude");
    this.elements.editAddressHidden = document.getElementById("edit-address");
    this.elements.editCityHidden = document.getElementById("edit-city");
    this.elements.editCountryHidden = document.getElementById("edit-country");
    this.elements.editCategorySelect = document.getElementById("edit-category");
    this.elements.editStatusSelect = document.getElementById("edit-status");
    this.elements.editSubmitBtn = document.getElementById(
      "edit-place-submit-btn"
    );
    this.elements.editPinOnMapBtn = document.getElementById(
      "edit-pin-on-map-btn"
    );
    this.elements.editMapPinInstruction = document.getElementById(
      "edit-map-pin-instruction"
    );
    this.elements.editCancelBtn =
      this.elements.editPlaceSection?.querySelector("button.cancel-btn");
    this.elements.reviewImageSection = document.getElementById(
      "review-image-section"
    );
    this.elements.reviewImageForm =
      document.getElementById("review-image-form");
    this.elements.reviewFormTitle =
      document.getElementById("review-form-title");
    this.elements.reviewTitleInput = document.getElementById("review-title");
    this.elements.reviewTextInput = document.getElementById("review-text");
    this.elements.reviewRatingStarsContainer = document.getElementById(
      "review-rating-stars"
    );
    this.elements.reviewRatingInput = document.getElementById("review-rating");
    this.elements.reviewImageInput = document.getElementById("review-image");
    this.elements.reviewRemoveImageCheckbox = document.getElementById(
      "review-remove-image"
    );
    this.elements.currentImageReviewSection = document.getElementById(
      "current-image-review-section"
    );
    this.elements.currentImageReviewThumb = document.getElementById(
      "current-image-review-thumb"
    );
    this.elements.reviewSubmitBtn = document.getElementById(
      "review-image-submit-btn"
    );
    this.elements.reviewCancelBtn =
      this.elements.reviewImageSection?.querySelector("button.cancel-btn");
    this.elements.seeReviewSection =
      document.getElementById("see-review-section");
    this.elements.seeReviewPlaceTitle = document.getElementById(
      "see-review-place-title"
    );
    this.elements.seeReviewRatingDisplay = document.getElementById(
      "see-review-rating-display"
    );
    this.elements.seeReviewDisplayTitle = document.getElementById(
      "see-review-display-title"
    );
    this.elements.seeReviewDisplayText = document.getElementById(
      "see-review-display-text"
    );
    this.elements.seeReviewDisplayImage = document.getElementById(
      "see-review-display-image"
    );
    this.elements.seeReviewEditBtn = document.getElementById(
      "see-review-edit-btn"
    );
    this.elements.seeReviewCloseBtn =
      this.elements.seeReviewSection?.querySelector("button.cancel-btn");
    this.elements.pinningMapContainer = document.getElementById(
      "pinning-map-container"
    );
    this.elements.pinningMapDiv = document.getElementById("pinning-map");
    this.elements.pinningMapControls = document.getElementById(
      "pinning-map-controls"
    );
    this.elements.confirmPinBtn = document.getElementById("confirm-pin-btn");
    this.elements.cancelPinBtn = document.getElementById("cancel-pin-btn");
  },
  setupEventListeners() {
    /* ... same ... */
    if (this.elements.toggleAddPlaceBtn)
      this.elements.toggleAddPlaceBtn.addEventListener("click", () => {
        if (
          this.elements.addPlaceWrapper?.style.display === "none" ||
          this.elements.addPlaceWrapper?.style.display === ""
        ) {
          this.showAddPlaceForm();
        } else {
          this.hideAddPlaceForm();
        }
      });
    if (this.elements.addPlaceCancelBtn)
      this.elements.addPlaceCancelBtn.addEventListener("click", () =>
        this.hideAddPlaceForm()
      );
    if (this.elements.addFindCoordsBtn)
      this.elements.addFindCoordsBtn.addEventListener("click", () =>
        this.handleGeocodeRequest("add")
      );
    if (this.elements.addPinOnMapBtn)
      this.elements.addPinOnMapBtn.addEventListener("click", () =>
        this.toggleMapPinning("add")
      );
    if (this.elements.editCancelBtn)
      this.elements.editCancelBtn.addEventListener("click", () =>
        this.hideEditPlaceForm()
      );
    if (this.elements.editFindCoordsBtn)
      this.elements.editFindCoordsBtn.addEventListener("click", () =>
        this.handleGeocodeRequest("edit")
      );
    if (this.elements.editPinOnMapBtn)
      this.elements.editPinOnMapBtn.addEventListener("click", () =>
        this.toggleMapPinning("edit")
      );
    if (this.elements.reviewCancelBtn)
      this.elements.reviewCancelBtn.addEventListener("click", () =>
        this.hideReviewForm()
      );
    if (this.elements.seeReviewCloseBtn)
      this.elements.seeReviewCloseBtn.addEventListener("click", () =>
        this.hideSeeReviewModal()
      );
    if (this.elements.seeReviewEditBtn) {
      this.elements.seeReviewEditBtn.addEventListener("click", () => {
        if (this.currentPlaceDataForReview) {
          this.showReviewForm(this.currentPlaceDataForReview);
        } else {
          alert("Error: Could not retrieve data to edit review.");
        }
      });
    }
    if (this.elements.confirmPinBtn) {
      this.elements.confirmPinBtn.addEventListener("click", () =>
        this.confirmPinLocation()
      );
    }
    if (this.elements.cancelPinBtn) {
      this.elements.cancelPinBtn.addEventListener("click", () => {
        if (this.pinningActiveForForm) {
          this.toggleMapPinning(this.pinningActiveForForm);
        }
      });
    }
    this.setupFormSubmission(
      this.elements.addPlaceForm,
      this.elements.addSubmitBtn,
      this.elements.addHiddenLat,
      this.elements.addHiddenLon,
      this.elements.addGeocodeStatus
    );
    this.setupFormSubmission(
      this.elements.editPlaceForm,
      this.elements.editSubmitBtn,
      this.elements.editLatitudeInput,
      this.elements.editLongitudeInput,
      this.elements.editGeocodeStatus
    );
    this.setupFormSubmission(
      this.elements.reviewImageForm,
      this.elements.reviewSubmitBtn
    );
    document.body.addEventListener("click", (event) => {
      if (event.target.closest(".image-overlay")) this.hideImageOverlay();
      else if (event.target.matches("#see-review-display-image"))
        this.showImageOverlay(event);
    });
  },
  setupFormSubmission(
    form,
    submitBtn,
    latInput = null,
    lonInput = null,
    statusEl = null
  ) {
    /* ... same ... */
    if (!form || !submitBtn) return;
    form.addEventListener("submit", (event) => {
      if (latInput && lonInput) {
        const latVal = parseFloat(latInput.value);
        const lonVal = parseFloat(lonInput.value);
        if (
          isNaN(latVal) ||
          isNaN(lonVal) ||
          latVal < -90 ||
          latVal > 90 ||
          lonVal < -180 ||
          lonVal > 180
        ) {
          event.preventDefault();
          this.setStatusMessage(
            statusEl || null,
            "Valid location coordinates are required to save.",
            "error"
          );
          submitBtn.disabled = true;
          return false;
        }
      }
      submitBtn.disabled = true;
      const originalText = submitBtn.textContent.replace(
        /^(Adding|Saving|Updating)...$/,
        "$1"
      );
      submitBtn.textContent = `${originalText}...`;
    });
  },
  hideAllSections() {
    /* ... same ... */
    if (this.elements.addPlaceWrapper)
      this.elements.addPlaceWrapper.style.display = "none";
    if (this.elements.editPlaceSection)
      this.elements.editPlaceSection.style.display = "none";
    if (this.elements.reviewImageSection)
      this.elements.reviewImageSection.style.display = "none";
    if (this.elements.seeReviewSection)
      this.elements.seeReviewSection.style.display = "none";
    if (this.pinningActiveForForm) {
      this.handlePinningModeChange(false, this.pinningActiveForForm);
      mapHandler.destroyPinningMap();
      this.pinningActiveForForm = null;
    }
    if (this.elements.pinningMapContainer) {
      this.elements.pinningMapContainer.style.display = "none";
    }
    if (this.elements.toggleAddPlaceBtn)
      this.elements.toggleAddPlaceBtn.textContent = "Add New Place";
  },
  showAddPlaceForm() {
    /* ... same ... */
    this.hideAllSections();
    this.resetAddPlaceForm();
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
    /* ... same ... */
    if (this.elements.addPlaceWrapper)
      this.elements.addPlaceWrapper.style.display = "none";
    if (this.elements.toggleAddPlaceBtn)
      this.elements.toggleAddPlaceBtn.textContent = "Add New Place";
    if (this.pinningActiveForForm === "add") {
      this.toggleMapPinning("add");
    }
  },
  showEditPlaceForm(placeDataInput) {
    /* ... same ... */
    let placeData;
    if (typeof placeDataInput === "string") {
      try {
        placeData = JSON.parse(placeDataInput);
      } catch (e) {
        console.error("Error parsing placeData JSON for edit:", e);
        alert("Error reading place data.");
        return;
      }
    } else if (typeof placeDataInput === "object" && placeDataInput !== null) {
      placeData = placeDataInput;
    } else {
      console.error(
        "Invalid input type for showEditPlaceForm:",
        placeDataInput
      );
      alert("Internal Error: Invalid data for edit form.");
      return;
    }
    this.currentPlaceDataForEdit = placeData;
    this.hideAllSections();
    try {
      const els = this.elements;
      if (!els.editPlaceSection || !els.editPlaceForm)
        throw new Error("Edit form elements missing");
      els.editPlaceFormTitle.textContent = `"${placeData.name || "Unknown"}"`;
      els.editNameInput.value = placeData.name || "";
      els.editCategorySelect.value = placeData.category || "other";
      els.editStatusSelect.value = placeData.status || "pending";
      els.editAddressInput.value = "";
      els.editLatitudeInput.value = placeData.latitude || "";
      els.editLongitudeInput.value = placeData.longitude || "";
      els.editAddressHidden.value = placeData.address || "";
      els.editCityHidden.value = placeData.city || "";
      els.editCountryHidden.value = placeData.country || "";
      els.editDisplayLat.textContent = placeData.latitude?.toFixed(6) ?? "N/A";
      els.editDisplayLon.textContent = placeData.longitude?.toFixed(6) ?? "N/A";
      this.setStatusMessage(els.editGeocodeStatus, "");
      els.editSubmitBtn.disabled = !(
        els.editLatitudeInput.value && els.editLongitudeInput.value
      );
      els.editSubmitBtn.textContent = "Save Changes";
      els.editPlaceForm.action = `/places/${placeData.id}/edit`;
      els.editPinOnMapBtn.textContent = "Pin New Location";
      els.editMapPinInstruction.style.display = "none";
      els.editAddressInput.disabled = false;
      els.editFindCoordsBtn.disabled = false;
      els.editPlaceSection.style.display = "block";
      els.editPlaceSection.scrollIntoView({
        behavior: "smooth",
        block: "start",
      });
    } catch (e) {
      console.error("Error populating edit form:", e);
      alert("Error preparing edit form.");
      this.hideAllSections();
      this.currentPlaceDataForEdit = null;
    }
  },
  hideEditPlaceForm() {
    /* ... same ... */
    if (this.elements.editPlaceSection)
      this.elements.editPlaceSection.style.display = "none";
    this.currentPlaceDataForEdit = null;
    if (this.pinningActiveForForm === "edit") {
      this.toggleMapPinning("edit");
    }
    if (
      !this.elements.addPlaceWrapper ||
      this.elements.addPlaceWrapper.style.display === "none"
    ) {
      if (this.elements.toggleAddPlaceBtn)
        this.elements.toggleAddPlaceBtn.textContent = "Add New Place";
    }
  },
  showReviewForm(placeDataInput) {
    /* ... same ... */
    let placeData;
    if (typeof placeDataInput === "string") {
      try {
        placeData = JSON.parse(placeDataInput);
      } catch (e) {
        console.error("Error parsing string input in showReviewForm:", e);
        alert("Internal error: Invalid Data String.");
        return;
      }
    } else if (typeof placeDataInput === "object" && placeDataInput !== null) {
      placeData = placeDataInput;
    } else {
      console.error("Invalid input type for showReviewForm.");
      alert("Internal error: Invalid Data Type.");
      return;
    }
    this.currentPlaceDataForReview = placeData;
    this.hideAllSections();
    try {
      const els = this.elements;
      if (!els.reviewImageSection || !els.reviewImageForm)
        throw new Error("Review form elements missing");
      if (!placeData || !placeData.id)
        throw new Error("placeData object is invalid or missing ID.");
      els.reviewFormTitle.textContent = `"${placeData.name || "Unknown"}"`;
      els.reviewTitleInput.value = placeData.review_title || "";
      els.reviewTextInput.value = placeData.review || "";
      const currentRating =
        placeData.rating !== null && placeData.rating !== undefined
          ? String(placeData.rating)
          : "";
      els.reviewRatingInput.value = currentRating;
      this.updateRatingStars(els.reviewRatingStarsContainer, currentRating);
      els.reviewImageInput.value = "";
      els.reviewRemoveImageCheckbox.checked = false;
      if (placeData.image_url && placeData.image_url.startsWith("http")) {
        els.currentImageReviewThumb.src = placeData.image_url;
        els.currentImageReviewSection.style.display = "block";
      } else {
        els.currentImageReviewSection.style.display = "none";
        els.currentImageReviewThumb.src = "";
      }
      els.reviewSubmitBtn.disabled = false;
      els.reviewSubmitBtn.textContent = "Save Review & Image";
      els.reviewImageForm.action = `/places/${placeData.id}/review-image`;
      els.reviewImageSection.style.display = "block";
      els.reviewImageSection.scrollIntoView({
        behavior: "smooth",
        block: "start",
      });
    } catch (e) {
      console.error("Error populating review form fields:", e);
      alert("Internal error: Cannot populate review form.");
      this.hideAllSections();
      this.currentPlaceDataForReview = null;
    }
  },
  hideReviewForm() {
    /* ... same ... */
    if (this.elements.reviewImageSection)
      this.elements.reviewImageSection.style.display = "none";
    this.currentPlaceDataForReview = null;
    if (
      (!this.elements.addPlaceWrapper ||
        this.elements.addPlaceWrapper.style.display === "none") &&
      (!this.elements.editPlaceSection ||
        this.elements.editPlaceSection.style.display === "none")
    ) {
      if (this.elements.toggleAddPlaceBtn)
        this.elements.toggleAddPlaceBtn.textContent = "Add New Place";
    }
  },
  showSeeReviewModal(placeDataInput) {
    /* ... same ... */
    let placeData;
    if (typeof placeDataInput === "string") {
      try {
        placeData = JSON.parse(placeDataInput);
      } catch (e) {
        console.error("Error parsing placeData JSON for see review:", e);
        alert("Error reading place data for review display.");
        return;
      }
    } else if (typeof placeDataInput === "object" && placeDataInput !== null) {
      placeData = placeDataInput;
    } else {
      console.error("Invalid input type for showSeeReviewModal.");
      alert("Internal Error: Invalid data for review modal.");
      return;
    }
    this.currentPlaceDataForReview = placeData;
    this.hideAllSections();
    try {
      const els = this.elements;
      if (!els.seeReviewSection)
        throw new Error("See Review modal elements missing");
      els.seeReviewPlaceTitle.textContent = `"${
        placeData.name || "Unknown Place"
      }"`;
      this.displayStaticRatingStars(
        els.seeReviewRatingDisplay,
        placeData.rating
      );
      els.seeReviewDisplayTitle.textContent = placeData.review_title || "";
      els.seeReviewDisplayText.textContent =
        placeData.review ||
        (placeData.review_title || placeData.rating
          ? ""
          : "(No review text entered)");
      els.seeReviewDisplayTitle.style.display = placeData.review_title
        ? "block"
        : "none";
      if (els.seeReviewDisplayImage) {
        if (placeData.image_url && placeData.image_url.startsWith("http")) {
          els.seeReviewDisplayImage.src = placeData.image_url;
          els.seeReviewDisplayImage.alt = `Image for ${
            placeData.name || "place"
          }`;
          els.seeReviewDisplayImage.style.display = "block";
        } else {
          els.seeReviewDisplayImage.style.display = "none";
          els.seeReviewDisplayImage.src = "";
        }
      }
      els.seeReviewSection.style.display = "block";
      els.seeReviewSection.scrollIntoView({
        behavior: "smooth",
        block: "start",
      });
    } catch (e) {
      console.error("Error populating see review modal:", e);
      alert("Error preparing review display.");
      this.hideAllSections();
      this.currentPlaceDataForReview = null;
    }
  },
  hideSeeReviewModal() {
    /* ... same ... */
    if (this.elements.seeReviewSection)
      this.elements.seeReviewSection.style.display = "none";
    this.currentPlaceDataForReview = null;
    if (
      (!this.elements.addPlaceWrapper ||
        this.elements.addPlaceWrapper.style.display === "none") &&
      (!this.elements.editPlaceSection ||
        this.elements.editPlaceSection.style.display === "none") &&
      (!this.elements.reviewImageSection ||
        this.elements.reviewImageSection.style.display === "none")
    ) {
      if (this.elements.toggleAddPlaceBtn)
        this.elements.toggleAddPlaceBtn.textContent = "Add New Place";
    }
  },
  async handleGeocodeRequest(formType = "add") {
    /* ... same ... */
    if (this.pinningActiveForForm === formType) {
      this.toggleMapPinning(formType);
    }
    const isEdit = formType === "edit";
    const addressQueryEl = isEdit
      ? this.elements.editAddressInput
      : this.elements.addAddressInput;
    const findBtn = isEdit
      ? this.elements.editFindCoordsBtn
      : this.elements.addFindCoordsBtn;
    const statusEl = isEdit
      ? this.elements.editGeocodeStatus
      : this.elements.addGeocodeStatus;
    const submitButton = isEdit
      ? this.elements.editSubmitBtn
      : this.elements.addSubmitBtn;
    if (!addressQueryEl || !findBtn || !statusEl || !submitButton) {
      this.setStatusMessage(
        statusEl || this.elements.addGeocodeStatus,
        "Internal page error: UI elements missing.",
        "error"
      );
      return;
    }
    const addressQuery = addressQueryEl.value.trim();
    if (!addressQuery) {
      this.setStatusMessage(
        statusEl,
        "Please enter an address or place name.",
        "error"
      );
      return;
    }
    this.setStatusMessage(statusEl, "Searching for location...", "loading");
    findBtn.disabled = true;
    submitButton.disabled = true;
    try {
      const geocodeUrl = `/api/v1/geocode?address=${encodeURIComponent(
        addressQuery
      )}`;
      const response = await apiClient.get(geocodeUrl);
      if (response.ok) {
        const result = await response.json();
        this.updateCoordsDisplay(result, formType);
        this.setStatusMessage(
          statusEl,
          `Location found: ${result.display_name}`,
          "success"
        );
        mapHandler.flyTo(result.latitude, result.longitude); // Fly main map
        submitButton.disabled = false;
      } else {
        let errorDetail = `Geocoding failed (${response.status}).`;
        try {
          const errorData = await response.json();
          errorDetail = errorData.detail || errorDetail;
        } catch (e) {
          /* ignore */
        }
        this.setStatusMessage(statusEl, `Error: ${errorDetail}`, "error");
      }
    } catch (error) {
      console.error("Geocoding fetch error:", error);
      this.setStatusMessage(
        statusEl,
        "Network error or server issue during geocoding.",
        "error"
      );
    } finally {
      if (findBtn) findBtn.disabled = false;
      const latInput = isEdit
        ? this.elements.editLatitudeInput
        : this.elements.addHiddenLat;
      const lonInput = isEdit
        ? this.elements.editLongitudeInput
        : this.elements.addHiddenLon;
      if (submitButton && latInput?.value && lonInput?.value) {
        submitButton.disabled = false;
      } else if (submitButton) {
        submitButton.disabled = true;
      }
    }
  },
  updateCoordsDisplay(coordsData, formType = "add") {
    /* ... same ... */
    const isEdit = formType === "edit";
    const els = this.elements;
    const coordsSect = isEdit ? els.editCoordsSection : els.addCoordsSection;
    const dispLatEl = isEdit ? els.editDisplayLat : els.addDisplayLat;
    const dispLonEl = isEdit ? els.editDisplayLon : els.addDisplayLon;
    const dispAddrEl = isEdit ? null : els.addDisplayAddress;
    const latInput = isEdit ? els.editLatitudeInput : els.addHiddenLat;
    const lonInput = isEdit ? els.editLongitudeInput : els.addHiddenLon;
    const addrHidden = isEdit ? els.editAddressHidden : els.addHiddenAddress;
    const cityHidden = isEdit ? els.editCityHidden : els.addHiddenCity;
    const countryHidden = isEdit ? els.editCountryHidden : els.addHiddenCountry;
    const submitButton = isEdit ? els.editSubmitBtn : els.addSubmitBtn;
    const statusEl = isEdit ? els.editGeocodeStatus : els.addGeocodeStatus;
    if (
      !coordsSect ||
      !dispLatEl ||
      !dispLonEl ||
      !latInput ||
      !lonInput ||
      !addrHidden ||
      !cityHidden ||
      !countryHidden ||
      !submitButton
    ) {
      console.error(
        "Cannot update coords display: Missing required elements for form type",
        formType
      );
      this.setStatusMessage(
        statusEl,
        "Internal UI Error updating coordinates.",
        "error"
      );
      return;
    }
    const lat = parseFloat(coordsData.latitude);
    const lon = parseFloat(coordsData.longitude);
    if (isNaN(lat) || isNaN(lon)) {
      this.setStatusMessage(
        statusEl,
        "Received invalid coordinate data.",
        "error"
      );
      submitButton.disabled = true;
      latInput.value = "";
      lonInput.value = "";
      dispLatEl.textContent = "N/A";
      dispLonEl.textContent = "N/A";
      if (dispAddrEl) dispAddrEl.textContent = "";
      coordsSect.style.display = "none";
      return;
    }
    latInput.value = lat.toFixed(7);
    lonInput.value = lon.toFixed(7);
    if (
      coordsData.address !== undefined ||
      coordsData.city !== undefined ||
      coordsData.country !== undefined ||
      coordsData.display_name !== undefined
    ) {
      addrHidden.value = coordsData.address || "";
      cityHidden.value = coordsData.city || "";
      countryHidden.value = coordsData.country || "";
    }
    dispLatEl.textContent = lat.toFixed(6);
    dispLonEl.textContent = lon.toFixed(6);
    if (dispAddrEl) {
      dispAddrEl.textContent =
        coordsData.display_name || "(Coordinates set via pin)";
    }
    coordsSect.style.display = "block";
    submitButton.disabled = false;
  },

  // --- Pinning Logic ---
  toggleMapPinning(formType = "add") {
    console.log(
      `UI: toggleMapPinning called for ${formType}. Current active: ${this.pinningActiveForForm}`
    );
    if (typeof L === "undefined") {
      alert("Mapping library (Leaflet) is not loaded. Cannot use pin feature.");
      console.error("Toggle Pinning failed: Leaflet (L) is undefined.");
      return;
    }

    if (this.pinningActiveForForm === formType) {
      // Turn OFF
      console.log(`UI: Turning OFF pinning for ${formType}`);
      this.pinningActiveForForm = null;
      mapHandler.destroyPinningMap();
      this.handlePinningModeChange(false, formType);
    } else {
      // Turn ON
      console.log(`UI: Turning ON pinning for ${formType}`);
      if (
        this.pinningActiveForForm !== null &&
        this.pinningActiveForForm !== formType
      ) {
        const otherForm = this.pinningActiveForForm;
        console.log(`UI: Deactivating pinning for other form: ${otherForm}`);
        this.pinningActiveForForm = null;
        mapHandler.destroyPinningMap();
        this.handlePinningModeChange(false, otherForm);
      }

      this.pinningActiveForForm = formType;
      const pinningMapContainer = this.elements.pinningMapContainer;
      if (!pinningMapContainer) {
        console.error("Pinning map container element not found!");
        alert("Error: Pinning map container is missing.");
        this.pinningActiveForForm = null;
        return;
      }

      // *** Move the container to the correct form section ***
      const targetFormSection =
        formType === "edit"
          ? this.elements.editPlaceSection
          : this.elements.addPlaceWrapper;
      const pinInstructionElement =
        formType === "edit"
          ? this.elements.editMapPinInstruction
          : this.elements.addMapPinInstruction;
      if (
        targetFormSection &&
        pinInstructionElement &&
        targetFormSection.contains(pinInstructionElement)
      ) {
        // Insert the map container *after* the instruction text
        pinInstructionElement.parentNode.insertBefore(
          pinningMapContainer,
          pinInstructionElement.nextSibling
        );
        console.log(
          `Moved pinning map container into ${formType} form section.`
        );
      } else {
        console.error(
          `Could not find target section or instruction element for ${formType} to insert map container.`
        );
        // Fallback: Append to body? Or just error out? Let's error for now.
        alert("Internal UI error: Could not place pinning map correctly.");
        this.pinningActiveForForm = null;
        return;
      }

      pinningMapContainer.style.display = "block"; // Make container visible *before* init

      let initialCoords = null;
      if (formType === "edit" && this.currentPlaceDataForEdit) {
        const lat = parseFloat(this.currentPlaceDataForEdit.latitude);
        const lng = parseFloat(this.currentPlaceDataForEdit.longitude);
        if (!isNaN(lat) && !isNaN(lng)) {
          initialCoords = { lat: lat, lng: lng };
        }
      }

      console.log("UI: Calling mapHandler.initPinningMap...");
      const mapInitialized = mapHandler.initPinningMap(
        "pinning-map",
        initialCoords
      );

      if (mapInitialized) {
        console.log("UI: Pinning map initialized. Placing marker...");
        mapHandler.placeDraggableMarker(initialCoords);
        this.handlePinningModeChange(true, formType); // Update button text etc.
        console.log("UI: Scrolling pinning map into view.");
        pinningMapContainer.scrollIntoView({
          behavior: "smooth",
          block: "nearest",
        });
      } else {
        console.error("UI: mapHandler.initPinningMap failed.");
        alert("Failed to initialize the pinning map. Please try again.");
        pinningMapContainer.style.display = "none";
        this.pinningActiveForForm = null;
        this.handlePinningModeChange(false, formType);
      }
    }
  },

  handlePinningModeChange(isActive, formType) {
    // Only updates UI elements (buttons, text), NOT map visibility
    console.debug(
      `UI: handlePinningModeChange - isActive: ${isActive}, formType: ${formType}`
    );
    const isEdit = formType === "edit";
    const pinBtn = isEdit
      ? this.elements.editPinOnMapBtn
      : this.elements.addPinOnMapBtn;
    const instructionEl = isEdit
      ? this.elements.editMapPinInstruction
      : this.elements.addMapPinInstruction;
    const addressInput = isEdit
      ? this.elements.editAddressInput
      : this.elements.addAddressInput;
    const findBtn = isEdit
      ? this.elements.editFindCoordsBtn
      : this.elements.addFindCoordsBtn;
    const statusEl = isEdit
      ? this.elements.editGeocodeStatus
      : this.elements.addGeocodeStatus;
    // No need to handle map container visibility here, toggleMapPinning does that

    if (!pinBtn || !instructionEl || !addressInput || !findBtn || !statusEl) {
      console.error(
        "handlePinningModeChange: Required UI elements missing for form",
        formType
      );
      return;
    }

    if (isActive) {
      addressInput.disabled = true;
      findBtn.disabled = true;
      instructionEl.style.display = "block";
      pinBtn.textContent = "Cancel Pinning";
      this.setStatusMessage(
        statusEl,
        "Drag the pin on the map, then confirm.",
        "info"
      );
      console.log(
        `handlePinningModeChange: Set UI for active pinning (${formType})`
      );
    } else {
      addressInput.disabled = false;
      findBtn.disabled = false;
      instructionEl.style.display = "none";
      pinBtn.textContent = isEdit ? "Pin New Location" : "Pin Location on Map";
      const latInput = isEdit
        ? this.elements.editLatitudeInput
        : this.elements.addHiddenLat;
      const lonInput = isEdit
        ? this.elements.editLongitudeInput
        : this.elements.addHiddenLon;
      const submitBtn = isEdit
        ? this.elements.editSubmitBtn
        : this.elements.addSubmitBtn;
      if (submitBtn) submitBtn.disabled = !(latInput?.value && lonInput?.value);
      console.log(
        `handlePinningModeChange: Set UI for inactive pinning (${formType})`
      );
    }
  },

  confirmPinLocation() {
    // No changes needed here
    console.log("UI: Confirm Pin clicked.");
    if (!this.pinningActiveForForm) {
      console.warn("Confirm Pin clicked but no form is active.");
      return;
    }
    const position = mapHandler.getDraggableMarkerPosition();
    const activeForm = this.pinningActiveForForm;
    const statusEl =
      activeForm === "edit"
        ? this.elements.editGeocodeStatus
        : this.elements.addGeocodeStatus;
    if (position) {
      const coords = { latitude: position.lat, longitude: position.lng };
      this.updateCoordsDisplay(coords, activeForm);
      this.setStatusMessage(statusEl, "Location set via map pin.", "success");
      this.toggleMapPinning(activeForm); // Deactivate pinning
    } else {
      console.error("Could not get marker position on confirm.");
      this.setStatusMessage(statusEl, "Error getting pin location.", "error");
      this.toggleMapPinning(activeForm); // Cancel on error
    }
  },
  // --- End Pinning Logic ---

  setupRatingStars() {
    /* ... same ... */ this.setupInteractiveStars(
      this.elements.reviewRatingStarsContainer,
      this.elements.reviewRatingInput
    );
  },
  setupInteractiveStars(container, hiddenInput) {
    /* ... same ... */ if (!container || !hiddenInput) return;
    const stars = container.querySelectorAll(".star");
    const setRating = (value) => {
      hiddenInput.value = value;
      this.updateRatingStars(container, value);
    };
    stars.forEach((star) => {
      star.addEventListener("click", (e) => {
        e.stopPropagation();
        const value = star.dataset.value;
        if (hiddenInput.value === value) {
          setRating("");
        } else {
          setRating(value);
        }
      });
      star.addEventListener("mouseover", () =>
        this.highlightStars(container, star.dataset.value)
      );
      star.addEventListener("mouseout", () =>
        this.updateRatingStars(container, hiddenInput.value)
      );
    });
    this.updateRatingStars(container, hiddenInput.value);
  },
  highlightStars(container, value) {
    /* ... same ... */ if (!container) return;
    const stars = container.querySelectorAll(".star");
    const val = parseInt(value, 10);
    stars.forEach((star) => {
      const starVal = parseInt(star.dataset.value, 10);
      const icon = star.querySelector("i");
      if (!icon) return;
      if (starVal <= val) {
        icon.classList.replace("far", "fas");
        star.classList.add("selected");
      } else {
        icon.classList.replace("fas", "far");
        star.classList.remove("selected");
      }
    });
  },
  updateRatingStars(container, selectedValue) {
    /* ... same ... */ if (!container) return;
    this.highlightStars(container, parseInt(selectedValue, 10) || 0);
  },
  displayStaticRatingStars(container, rating) {
    /* ... same ... */ if (!container) return;
    const numRating = parseInt(rating, 10);
    if (numRating >= 1 && numRating <= 5) {
      let html = "";
      for (let i = 1; i <= 5; i++) {
        html += `<i class="${i <= numRating ? "fas" : "far"} fa-star"></i> `;
      }
      container.innerHTML = html.trim();
      container.style.display = "inline-block";
    } else {
      container.innerHTML = "(No rating)";
      container.style.display = "inline-block";
    }
  },
  setStatusMessage(element, message, type = "info") {
    /* ... same ... */ if (!element) {
      console.warn(
        "setStatusMessage called with null element for message:",
        message
      );
      return;
    }
    element.textContent = message;
    element.className = "status-message";
    if (type === "error") {
      element.classList.add("error-message");
    } else if (type === "success") {
      element.classList.add("success-message");
    } else if (type === "loading") {
      element.classList.add("loading-indicator");
    } else {
      element.classList.add("info-message");
    }
    element.style.display = message ? "block" : "none";
  },
  resetAddPlaceForm() {
    /* ... same ... */ if (this.elements.addPlaceForm)
      this.elements.addPlaceForm.reset();
    if (this.elements.addCoordsSection)
      this.elements.addCoordsSection.style.display = "none";
    this.setStatusMessage(this.elements.addGeocodeStatus, "");
    if (this.elements.addHiddenLat) this.elements.addHiddenLat.value = "";
    if (this.elements.addHiddenLon) this.elements.addHiddenLon.value = "";
    if (this.elements.addHiddenAddress)
      this.elements.addHiddenAddress.value = "";
    if (this.elements.addHiddenCity) this.elements.addHiddenCity.value = "";
    if (this.elements.addHiddenCountry)
      this.elements.addHiddenCountry.value = "";
    if (this.elements.addDisplayLat)
      this.elements.addDisplayLat.textContent = "";
    if (this.elements.addDisplayLon)
      this.elements.addDisplayLon.textContent = "";
    if (this.elements.addDisplayAddress)
      this.elements.addDisplayAddress.textContent = "";
    if (this.elements.addAddressInput) this.elements.addAddressInput.value = "";
    if (this.elements.addSubmitBtn) this.elements.addSubmitBtn.disabled = true;
    if (this.elements.addPinOnMapBtn)
      this.elements.addPinOnMapBtn.textContent = "Pin Location on Map";
    if (this.elements.addMapPinInstruction)
      this.elements.addMapPinInstruction.style.display = "none";
    if (this.elements.addAddressInput)
      this.elements.addAddressInput.disabled = false;
    if (this.elements.addFindCoordsBtn)
      this.elements.addFindCoordsBtn.disabled = false;
    if (this.pinningActiveForForm === "add") {
      this.toggleMapPinning("add");
    }
  },
  showImageOverlay(event) {
    /* ... same ... */ const clickedImage = event.target;
    if (
      !clickedImage ||
      clickedImage.tagName !== "IMG" ||
      !clickedImage.src ||
      !clickedImage.src.startsWith("http")
    ) {
      console.debug("showImageOverlay: Click target not a valid image.");
      return;
    }
    let overlay = document.querySelector(".image-overlay");
    if (!overlay) {
      overlay = document.createElement("div");
      overlay.className = "image-overlay";
      const img = document.createElement("img");
      img.alt = clickedImage.alt || "Enlarged image";
      img.onclick = (e) => e.stopPropagation();
      overlay.appendChild(img);
      overlay.onclick = this.hideImageOverlay.bind(this);
      document.body.appendChild(overlay);
    }
    overlay.querySelector("img").src = clickedImage.src;
    setTimeout(() => overlay.classList.add("visible"), 10);
  },
  hideImageOverlay() {
    /* ... same ... */ const overlay = document.querySelector(
      ".image-overlay.visible"
    );
    if (overlay) {
      overlay.classList.remove("visible");
      overlay.addEventListener(
        "transitionend",
        () => {
          if (document.body.contains(overlay)) {
            document.body.removeChild(overlay);
          }
        },
        { once: true }
      );
    }
  },
};

export default ui;
