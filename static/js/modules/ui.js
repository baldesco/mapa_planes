/**
 * ui.js
 * Module for handling general UI interactions, form display, DOM updates,
 * modals, rating stars, and geocoding requests.
 */
import apiClient from "./apiClient.js";
import mapHandler from "./mapHandler.js"; // Still needed for flyTo

const ui = {
  // --- DOM Element References ---
  elements: {
    /* ... same as before ... */
    // Add Place Form
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

    // Edit Place Form
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

    // Review/Image Form
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

    // See Review Modal
    seeReviewSection: null,
    seeReviewPlaceTitle: null,
    seeReviewRatingDisplay: null,
    seeReviewDisplayTitle: null,
    seeReviewDisplayText: null,
    seeReviewDisplayImage: null,
    seeReviewEditBtn: null,
    seeReviewCloseBtn: null,
  },

  // --- State ---
  currentPlaceDataForEdit: null,
  currentPlaceDataForReview: null,
  pinningActiveForForm: null, // NEW STATE: null, 'add', or 'edit'

  /** Initialize the UI module */
  init() {
    console.debug("UI Module: Initializing...");
    this.cacheDOMElements();
    this.setupEventListeners();
    this.setupRatingStars();

    // Expose necessary functions globally for inline HTML handlers AND iframe communication
    window.showAddPlaceForm = this.showAddPlaceForm.bind(this);
    window.hideAddPlaceForm = this.hideAddPlaceForm.bind(this);
    window.showEditPlaceForm = this.showEditPlaceForm.bind(this);
    window.showReviewForm = this.showReviewForm.bind(this);
    window.showSeeReviewModal = this.showSeeReviewModal.bind(this);
    window.showImageOverlay = this.showImageOverlay.bind(this);
    // Expose functions needed by the iframe script
    window.isPinningActive = this.isPinningActive.bind(this);
    window.handleMapPinClick = this.handleMapPinClick.bind(this);
    window.ui = this; // Expose entire module for easier debugging if needed

    this.hideAllSections(); // This now also resets pinningActiveForForm
    if (this.elements.addSubmitBtn) this.elements.addSubmitBtn.disabled = true;
    if (this.elements.editSubmitBtn)
      this.elements.editSubmitBtn.disabled = true;

    // Enable pin buttons (they no longer depend on mapHandler init for pinning)
    if (this.elements.addPinOnMapBtn)
      this.elements.addPinOnMapBtn.disabled = false;
    if (this.elements.editPinOnMapBtn)
      this.elements.editPinOnMapBtn.disabled = false;

    console.log("UI Module: Initialization Complete.");
  },

  /** Cache DOM elements */
  cacheDOMElements() {
    /* ... same as before ... */
    // Add Place Form Elements
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

    // Edit Place Form Elements (Core Details Only)
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

    // Review/Image Form Elements
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

    // See Review Modal Elements
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
  },

  /** Setup primary event listeners */
  setupEventListeners() {
    // Toggle Add Place Form Button
    if (this.elements.toggleAddPlaceBtn) {
      /* ... listener same ... */
      this.elements.toggleAddPlaceBtn.addEventListener("click", () => {
        if (
          !this.elements.addPlaceWrapper ||
          this.elements.addPlaceWrapper.style.display === "none" ||
          this.elements.addPlaceWrapper.style.display === ""
        ) {
          this.showAddPlaceForm();
        } else {
          this.hideAddPlaceForm();
        }
      });
    }
    // Add Place Form Buttons
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
      ); // Calls UI toggle, not mapHandler

    // Edit Place Form Buttons
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
      ); // Calls UI toggle, not mapHandler

    // Review/Image Form Buttons
    if (this.elements.reviewCancelBtn)
      this.elements.reviewCancelBtn.addEventListener("click", () =>
        this.hideReviewForm()
      );

    // See Review Modal Buttons
    if (this.elements.seeReviewCloseBtn)
      this.elements.seeReviewCloseBtn.addEventListener("click", () =>
        this.hideSeeReviewModal()
      );
    if (this.elements.seeReviewEditBtn) {
      /* ... listener same ... */
      this.elements.seeReviewEditBtn.addEventListener("click", () => {
        if (this.currentPlaceDataForReview) {
          this.showReviewForm(this.currentPlaceDataForReview);
        } else {
          alert("Error: Could not retrieve data to edit review.");
        }
      });
    }

    // Form Submissions
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

    // Image overlay click listener (delegated)
    document.body.addEventListener("click", (event) => {
      if (event.target.closest(".image-overlay")) {
        this.hideImageOverlay();
      } else if (event.target.matches("#see-review-display-image")) {
        this.showImageOverlay(event);
      }
    });
  },

  /** Helper to set up common form submission logic */
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
      if (latInput && lonInput && (!latInput.value || !lonInput.value)) {
        event.preventDefault();
        this.setStatusMessage(
          statusEl || null,
          "Location coordinates missing.",
          "error"
        );
        submitBtn.disabled = true;
        return false;
      }
      submitBtn.disabled = true;
      submitBtn.textContent = submitBtn.textContent.replace(
        /^(Add|Save|Update)/,
        "$1ing..."
      );
    });
  },

  /** Hide all collapsible sections */
  hideAllSections() {
    if (this.elements.addPlaceWrapper)
      this.elements.addPlaceWrapper.style.display = "none";
    if (this.elements.editPlaceSection)
      this.elements.editPlaceSection.style.display = "none";
    if (this.elements.reviewImageSection)
      this.elements.reviewImageSection.style.display = "none";
    if (this.elements.seeReviewSection)
      this.elements.seeReviewSection.style.display = "none";
    if (this.elements.toggleAddPlaceBtn)
      this.elements.toggleAddPlaceBtn.textContent = "Add New Place";
    // Reset pinning state when hiding sections
    this.pinningActiveForForm = null;
    // Reset pin button texts visually (though state is handled by pinningActiveForForm)
    if (this.elements.addPinOnMapBtn)
      this.elements.addPinOnMapBtn.textContent = "Pin Location on Map";
    if (this.elements.editPinOnMapBtn)
      this.elements.editPinOnMapBtn.textContent = "Pin Location on Map";
    if (this.elements.addMapPinInstruction)
      this.elements.addMapPinInstruction.style.display = "none";
    if (this.elements.editMapPinInstruction)
      this.elements.editMapPinInstruction.style.display = "none";
  },

  // ... show/hide/reset form functions remain largely the same,
  // BUT they no longer call mapHandler directly ...
  showAddPlaceForm() {
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
    if (this.elements.addPlaceWrapper)
      this.elements.addPlaceWrapper.style.display = "none";
    if (this.elements.toggleAddPlaceBtn)
      this.elements.toggleAddPlaceBtn.textContent = "Add New Place";
    this.pinningActiveForForm = null; /* Ensure pinning state is reset */
  },
  showEditPlaceForm(placeDataInput) {
    /* ... (population logic same, removing review/rating fields) ... */
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
      els.editPlaceFormTitle.textContent = placeData.name || "Unknown";
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
      els.editPinOnMapBtn.textContent = "Pin Location on Map";
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
    if (this.elements.editPlaceSection)
      this.elements.editPlaceSection.style.display = "none";
    this.currentPlaceDataForEdit = null;
    this.pinningActiveForForm = null;
    /* Ensure pinning state is reset */ if (
      !this.elements.addPlaceWrapper ||
      this.elements.addPlaceWrapper.style.display === "none"
    ) {
      if (this.elements.toggleAddPlaceBtn)
        this.elements.toggleAddPlaceBtn.textContent = "Add New Place";
    }
  },
  showReviewForm(placeDataInput) {
    /* ... same logic ... */
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
      els.reviewFormTitle.textContent = placeData.name || "Unknown";
      els.reviewTitleInput.value = placeData.review_title || "";
      els.reviewTextInput.value = placeData.review || "";
      els.reviewRatingInput.value = placeData.rating || "";
      this.updateRatingStars(els.reviewRatingStarsContainer, placeData.rating);
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
    /* ... same logic ... */
    if (this.elements.reviewImageSection)
      this.elements.reviewImageSection.style.display = "none";
    this.currentPlaceDataForReview = null;
    if (
      !this.elements.addPlaceWrapper ||
      this.elements.addPlaceWrapper.style.display === "none"
    ) {
      if (this.elements.toggleAddPlaceBtn)
        this.elements.toggleAddPlaceBtn.textContent = "Add New Place";
    }
  },
  showSeeReviewModal(placeDataInput) {
    /* ... same logic ... */
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
      els.seeReviewPlaceTitle.textContent = placeData.name || "Unknown Place";
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
    /* ... same logic ... */
    if (this.elements.seeReviewSection)
      this.elements.seeReviewSection.style.display = "none";
    this.currentPlaceDataForReview = null;
    if (
      !this.elements.addPlaceWrapper ||
      this.elements.addPlaceWrapper.style.display === "none"
    ) {
      if (this.elements.toggleAddPlaceBtn)
        this.elements.toggleAddPlaceBtn.textContent = "Add New Place";
    }
  },

  /** Handle Geocode Request */
  async handleGeocodeRequest(formType = "add") {
    /* ... same logic ... */
    // mapHandler.stopPinningMode(); // No need to call mapHandler here
    this.pinningActiveForForm = null; // Ensure UI state is reset
    this.handlePinningModeChange(false, formType); // Update UI visually

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
        "Internal page error.",
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
    this.setStatusMessage(statusEl, "Searching...", "loading");
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
        mapHandler.flyTo(result.latitude, result.longitude);
      } // Still use mapHandler for flyTo
      else {
        let errorDetail = `Geocoding failed (${response.status}).`;
        try {
          const errorData = await response.json();
          errorDetail = errorData.detail || errorDetail;
        } catch (e) {}
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
      const latVal = isEdit
        ? this.elements.editLatitudeInput.value
        : this.elements.addHiddenLat.value;
      const lonVal = isEdit
        ? this.elements.editLongitudeInput.value
        : this.elements.addHiddenLon.value;
      if (submitButton) submitButton.disabled = !(latVal && lonVal);
    }
  },

  /** Update coordinate display fields */
  updateCoordsDisplay(coordsData, formType = "add") {
    /* ... same logic ... */
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
      return;
    }
    const lat = parseFloat(coordsData.latitude);
    const lon = parseFloat(coordsData.longitude);
    if (isNaN(lat) || isNaN(lon)) {
      this.setStatusMessage(
        statusEl,
        "Invalid coordinate data received.",
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
    latInput.value = lat;
    lonInput.value = lon;
    if (
      coordsData.display_name !== undefined ||
      coordsData.address !== undefined
    ) {
      addrHidden.value = coordsData.address || "";
      cityHidden.value = coordsData.city || "";
      countryHidden.value = coordsData.country || "";
    }
    dispLatEl.textContent = lat.toFixed(6);
    dispLonEl.textContent = lon.toFixed(6);
    if (dispAddrEl)
      dispAddrEl.textContent =
        coordsData.display_name || "(Coordinates set manually)";
    coordsSect.style.display = "block";
    submitButton.disabled = false;
  },

  /** Toggle map pinning mode (UI only) */
  toggleMapPinning(formType = "add") {
    console.log(`UI: toggleMapPinning called for ${formType}`);
    // If currently pinning for *this* form, turn it off
    if (this.pinningActiveForForm === formType) {
      this.pinningActiveForForm = null;
      this.handlePinningModeChange(false, formType); // Update UI
    } else {
      // If pinning for the *other* form, turn that off first
      if (this.pinningActiveForForm !== null) {
        this.handlePinningModeChange(false, this.pinningActiveForForm);
      }
      // Turn pinning on for *this* form
      this.pinningActiveForForm = formType;
      this.handlePinningModeChange(true, formType); // Update UI
    }
  },

  /** Update UI based on pinning mode state */
  handlePinningModeChange(isActive, formType) {
    console.debug(
      `UI: Updating UI for pinning mode change: ${isActive} for ${formType}`
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

    if (!pinBtn || !instructionEl || !addressInput || !findBtn || !statusEl)
      return;

    if (isActive) {
      addressInput.disabled = true;
      findBtn.disabled = true;
      instructionEl.style.display = "block";
      pinBtn.textContent = "Cancel Pinning";
      this.setStatusMessage(
        statusEl,
        "Click the map to set the location.",
        "info"
      );
      // Add a class to body perhaps? To change map cursor via CSS?
      document.body.classList.add("map-pinning-active");
    } else {
      addressInput.disabled = false;
      findBtn.disabled = false;
      instructionEl.style.display = "none";
      pinBtn.textContent = "Pin Location on Map";
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
      document.body.classList.remove("map-pinning-active");
    }
  },

  /** Function called by iframe when map is clicked */
  handleMapPinClick(lat, lng) {
    console.log(
      `UI: Received map pin click from iframe: Lat: ${lat}, Lng: ${lng}`
    );
    if (this.pinningActiveForForm) {
      const coords = { latitude: lat, longitude: lng };
      // Update the coordinates for the currently active form
      this.updateCoordsDisplay(coords, this.pinningActiveForForm);
      // Update status message
      const statusEl =
        this.pinningActiveForForm === "edit"
          ? this.elements.editGeocodeStatus
          : this.elements.addGeocodeStatus;
      this.setStatusMessage(statusEl, "Location pinned via map.", "success");
      // Automatically turn off pinning mode after successful pin
      this.toggleMapPinning(this.pinningActiveForForm);
    } else {
      console.warn(
        "UI: Map click received from iframe, but no form is in pinning mode."
      );
    }
  },

  /** Check if pinning is active (for iframe) */
  isPinningActive() {
    // console.debug(`UI: isPinningActive check called, returning: ${this.pinningActiveForForm !== null}`);
    return this.pinningActiveForForm !== null;
  },

  // --- Rating Stars ---
  setupRatingStars() {
    /* ... same logic ... */
    this.setupInteractiveStars(
      this.elements.reviewRatingStarsContainer,
      this.elements.reviewRatingInput
    );
  },
  setupInteractiveStars(container, hiddenInput) {
    /* ... same logic ... */
    if (!container || !hiddenInput) return;
    const stars = container.querySelectorAll(".star");
    stars.forEach((star) => {
      star.addEventListener("click", (e) => {
        e.stopPropagation();
        hiddenInput.value = star.dataset.value;
        this.updateRatingStars(container, hiddenInput.value);
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
    /* ... same logic ... */
    if (!container) return;
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
    /* ... same logic ... */
    if (!container) return;
    this.highlightStars(container, parseInt(selectedValue, 10) || 0);
  },
  displayStaticRatingStars(container, rating) {
    /* ... same logic ... */
    if (!container) return;
    const numRating = parseInt(rating, 10);
    if (numRating >= 1 && numRating <= 5) {
      let html = "";
      for (let i = 1; i <= 5; i++)
        html += `<i class="${i <= numRating ? "fas" : "far"} fa-star"></i> `;
      container.innerHTML = html.trim();
      container.style.display = "inline-block";
    } else {
      container.innerHTML = "(No rating)";
      container.style.display = "inline-block";
    }
  },

  // --- Utilities ---
  setStatusMessage(element, message, type = "info") {
    /* ... same logic ... */
    if (!element) return;
    element.textContent = message;
    element.className = "status-message";
    if (type === "error") element.classList.add("error-message");
    else if (type === "success") element.classList.add("success-message");
    else if (type === "loading") element.classList.add("loading-indicator");
    else element.classList.add("info-message");
    element.style.display = message ? "block" : "none";
  },
  resetAddPlaceForm() {
    /* ... same logic, including resetting pin button text ... */
    if (this.elements.addPlaceForm) this.elements.addPlaceForm.reset();
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
    if (this.elements.addSubmitBtn) this.elements.addSubmitBtn.disabled = true;
    if (this.elements.addDisplayLat)
      this.elements.addDisplayLat.textContent = "";
    if (this.elements.addDisplayLon)
      this.elements.addDisplayLon.textContent = "";
    if (this.elements.addDisplayAddress)
      this.elements.addDisplayAddress.textContent = "";
    if (this.elements.addAddressInput) this.elements.addAddressInput.value = "";
    // Also reset UI state for pinning button
    if (this.elements.addPinOnMapBtn)
      this.elements.addPinOnMapBtn.textContent = "Pin Location on Map";
    if (this.elements.addMapPinInstruction)
      this.elements.addMapPinInstruction.style.display = "none";
    if (this.elements.addAddressInput)
      this.elements.addAddressInput.disabled = false;
    if (this.elements.addFindCoordsBtn)
      this.elements.addFindCoordsBtn.disabled = false;
  },
  showImageOverlay(event) {
    /* ... same logic ... */
    const clickedImage = event.target;
    if (
      !clickedImage ||
      clickedImage.tagName !== "IMG" ||
      !clickedImage.src ||
      !clickedImage.src.startsWith("http")
    )
      return;
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
    /* ... same logic ... */
    const overlay = document.querySelector(".image-overlay.visible");
    if (overlay) {
      overlay.classList.remove("visible");
      overlay.addEventListener(
        "transitionend",
        () => {
          if (document.body.contains(overlay))
            document.body.removeChild(overlay);
        },
        { once: true }
      );
    }
  },
};

export default ui;
