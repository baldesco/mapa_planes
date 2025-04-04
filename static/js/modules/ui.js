/**
 * ui.js
 * Module for handling general UI interactions, form display, DOM updates,
 * modals, rating stars, and geocoding requests.
 */
import apiClient from "./apiClient.js";
import mapHandler from "./mapHandler.js"; // To interact with map for pinning/flying

const ui = {
  // --- DOM Element References ---
  elements: {
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
    editReviewTitleInput: null,
    editReviewTextInput: null,
    editRatingStarsContainer: null,
    editRatingInput: null,
    editRemoveImageCheckbox: null,
    editSubmitBtn: null,
    editPinOnMapBtn: null,
    editMapPinInstruction: null,
    editCancelBtn: null, // Added specific cancel button

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
    reviewCancelBtn: null, // Added specific cancel button

    // See Review Modal
    seeReviewSection: null,
    seeReviewPlaceTitle: null,
    seeReviewRatingDisplay: null,
    seeReviewDisplayTitle: null,
    seeReviewDisplayText: null,
    seeReviewDisplayImage: null,
    seeReviewEditBtn: null,
    seeReviewCloseBtn: null, // Added specific close button
  },

  // --- State ---
  currentPlaceDataForEdit: null, // Store data when edit form opens
  currentPlaceDataForReview: null, // Store data when review form opens

  /**
   * Initialize the UI module. Cache DOM elements and setup listeners.
   */
  init() {
    console.debug("UI Module: Initializing...");
    this.cacheDOMElements();
    this.setupEventListeners();
    this.setupRatingStars();

    // Expose necessary functions globally for inline HTML handlers (onclick)
    // This is a bridge until event delegation is fully implemented
    window.showAddPlaceForm = this.showAddPlaceForm.bind(this);
    window.hideAddPlaceForm = this.hideAddPlaceForm.bind(this);
    window.showEditPlaceForm = this.showEditPlaceForm.bind(this);
    // window.hideEditPlaceForm = this.hideEditPlaceForm.bind(this); // Use cancel btn listener
    window.showReviewForm = this.showReviewForm.bind(this);
    // window.hideReviewForm = this.hideReviewForm.bind(this); // Use cancel btn listener
    window.showSeeReviewModal = this.showSeeReviewModal.bind(this);
    // window.hideSeeReviewModal = this.hideSeeReviewModal.bind(this); // Use cancel btn listener
    window.showImageOverlay = this.showImageOverlay.bind(this);

    // Initial UI state
    this.hideAllSections();
    if (this.elements.addSubmitBtn) this.elements.addSubmitBtn.disabled = true;
    if (this.elements.editSubmitBtn)
      this.elements.editSubmitBtn.disabled = true;

    console.log("UI Module: Initialization Complete.");
  },

  /**
   * Find and store references to frequently used DOM elements.
   */
  cacheDOMElements() {
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
    this.elements.editReviewTitleInput =
      document.getElementById("edit-review-title");
    this.elements.editReviewTextInput =
      document.getElementById("edit-review-text");
    this.elements.editRatingStarsContainer =
      document.getElementById("edit-rating-stars");
    this.elements.editRatingInput = document.getElementById("edit-rating");
    this.elements.editRemoveImageCheckbox =
      document.getElementById("edit-remove-image");
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

    // Check if all essential elements were found
    const essential = [
      this.elements.addPlaceWrapper,
      this.elements.editPlaceSection,
      this.elements.reviewImageSection,
      this.elements.seeReviewSection,
    ];
    if (essential.some((el) => !el)) {
      console.warn("UI Init: One or more main section wrappers not found.");
    }
  },

  /**
   * Setup primary event listeners for buttons and forms.
   */
  setupEventListeners() {
    // Toggle Add Place Form Button
    if (this.elements.toggleAddPlaceBtn) {
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
    if (this.elements.addPlaceCancelBtn) {
      this.elements.addPlaceCancelBtn.addEventListener("click", () =>
        this.hideAddPlaceForm()
      );
    }
    if (this.elements.addFindCoordsBtn) {
      this.elements.addFindCoordsBtn.addEventListener("click", () =>
        this.handleGeocodeRequest("add")
      );
    }
    if (this.elements.addPinOnMapBtn) {
      this.elements.addPinOnMapBtn.addEventListener("click", () =>
        this.toggleMapPinning("add")
      );
    }

    // Edit Place Form Buttons
    if (this.elements.editCancelBtn) {
      this.elements.editCancelBtn.addEventListener("click", () =>
        this.hideEditPlaceForm()
      );
    }
    if (this.elements.editFindCoordsBtn) {
      this.elements.editFindCoordsBtn.addEventListener("click", () =>
        this.handleGeocodeRequest("edit")
      );
    }
    if (this.elements.editPinOnMapBtn) {
      this.elements.editPinOnMapBtn.addEventListener("click", () =>
        this.toggleMapPinning("edit")
      );
    }

    // Review/Image Form Buttons
    if (this.elements.reviewCancelBtn) {
      this.elements.reviewCancelBtn.addEventListener("click", () =>
        this.hideReviewForm()
      );
    }

    // See Review Modal Buttons
    if (this.elements.seeReviewCloseBtn) {
      this.elements.seeReviewCloseBtn.addEventListener("click", () =>
        this.hideSeeReviewModal()
      );
    }
    if (this.elements.seeReviewEditBtn) {
      this.elements.seeReviewEditBtn.addEventListener("click", (event) => {
        // Retrieve stored data and show the appropriate edit form
        if (this.currentPlaceDataForReview) {
          console.log("Editing review from 'See Review' modal...");
          this.showReviewForm(this.currentPlaceDataForReview); // Pass the stored data object
        } else {
          alert("Error: Could not retrieve data to edit review.");
          console.error("Missing currentPlaceDataForReview on edit click.");
        }
      });
    }

    // Form Submissions (basic validation and disabling submit button)
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
    ); // No coordinate check needed

    // Image overlay click listener (delegated)
    document.body.addEventListener("click", (event) => {
      if (event.target.closest(".image-overlay")) {
        this.hideImageOverlay();
      } else if (event.target.matches("#see-review-display-image")) {
        this.showImageOverlay(event); // Handle click on the thumbnail too
      }
    });
  },

  /**
   * Helper to set up common form submission logic (disable button, basic coord check).
   */
  setupFormSubmission(
    form,
    submitBtn,
    latInput = null,
    lonInput = null,
    statusEl = null
  ) {
    if (!form || !submitBtn) return;

    form.addEventListener("submit", (event) => {
      // Check coordinates if inputs are provided
      if (latInput && lonInput && (!latInput.value || !lonInput.value)) {
        event.preventDefault();
        this.setStatusMessage(
          statusEl || null,
          'Location coordinates missing. Use "Find" or "Pin" button first.',
          "error"
        );
        submitBtn.disabled = true; // Ensure button is disabled
        return false;
      }
      // Disable button to prevent multiple submissions
      submitBtn.disabled = true;
      submitBtn.textContent = submitBtn.textContent.replace(
        /^(Add|Save|Update)/,
        "$1ing..."
      ); // Simple text change
    });
  },

  // --- Section Visibility Control ---
  hideAllSections() {
    if (this.elements.addPlaceWrapper)
      this.elements.addPlaceWrapper.style.display = "none";
    if (this.elements.editPlaceSection)
      this.elements.editPlaceSection.style.display = "none";
    if (this.elements.reviewImageSection)
      this.elements.reviewImageSection.style.display = "none";
    if (this.elements.seeReviewSection)
      this.elements.seeReviewSection.style.display = "none";

    // Reset Add Place button text if it exists
    if (this.elements.toggleAddPlaceBtn) {
      this.elements.toggleAddPlaceBtn.textContent = "Add New Place";
    }
    // Ensure map pinning is stopped if any section is hidden this way
    mapHandler.stopPinningMode();
  },

  showAddPlaceForm() {
    this.hideAllSections(); // Hide others first
    this.resetAddPlaceForm(); // Clear previous data
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
    mapHandler.stopPinningMode(); // Ensure pinning stops
    // Optional: Reset form on explicit cancel?
    // this.resetAddPlaceForm();
  },

  showEditPlaceForm(placeDataInput) {
    let placeData;
    // Handle both JSON string (from inline onclick) and object (internal calls)
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

    this.currentPlaceDataForEdit = placeData; // Store for potential use
    this.hideAllSections();

    try {
      // Populate Edit Form fields
      const els = this.elements;
      if (!els.editPlaceSection || !els.editPlaceForm)
        throw new Error("Edit form elements missing");

      els.editPlaceFormTitle.textContent = placeData.name || "Unknown";
      els.editNameInput.value = placeData.name || "";
      els.editCategorySelect.value = placeData.category || "other";
      els.editStatusSelect.value = placeData.status || "pending";
      els.editAddressInput.value = ""; // Clear geocode input
      els.editLatitudeInput.value = placeData.latitude || "";
      els.editLongitudeInput.value = placeData.longitude || "";
      els.editAddressHidden.value = placeData.address || ""; // Store original address parts
      els.editCityHidden.value = placeData.city || "";
      els.editCountryHidden.value = placeData.country || "";
      els.editDisplayLat.textContent = placeData.latitude?.toFixed(6) ?? "N/A";
      els.editDisplayLon.textContent = placeData.longitude?.toFixed(6) ?? "N/A";
      this.setStatusMessage(els.editGeocodeStatus, ""); // Clear status
      els.editSubmitBtn.disabled = !(
        els.editLatitudeInput.value && els.editLongitudeInput.value
      );
      els.editSubmitBtn.textContent = "Save Changes"; // Reset button text
      els.editPlaceForm.action = `/places/${placeData.id}/edit`; // Set correct form action URL

      els.editReviewTitleInput.value = placeData.review_title || "";
      els.editReviewTextInput.value = placeData.review || "";
      els.editRatingInput.value = placeData.rating || "";
      this.updateRatingStars(els.editRatingStarsContainer, placeData.rating);
      els.editRemoveImageCheckbox.checked = false; // Reset checkbox

      // Reset pinning button state
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
      this.hideAllSections(); // Hide potentially broken form
      this.currentPlaceDataForEdit = null;
    }
  },

  hideEditPlaceForm() {
    if (this.elements.editPlaceSection)
      this.elements.editPlaceSection.style.display = "none";
    this.currentPlaceDataForEdit = null;
    mapHandler.stopPinningMode(); // Ensure pinning stops
    // Restore "Add New Place" button text if add form is also hidden
    if (
      !this.elements.addPlaceWrapper ||
      this.elements.addPlaceWrapper.style.display === "none"
    ) {
      if (this.elements.toggleAddPlaceBtn)
        this.elements.toggleAddPlaceBtn.textContent = "Add New Place";
    }
  },

  showReviewForm(placeDataInput) {
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

    this.currentPlaceDataForReview = placeData; // Store for potential use (e.g., edit from 'See Review')
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
      els.reviewImageInput.value = ""; // Clear file input
      els.reviewRemoveImageCheckbox.checked = false; // Reset checkbox

      // Show current image thumbnail if available
      if (placeData.image_url && placeData.image_url.startsWith("http")) {
        els.currentImageReviewThumb.src = placeData.image_url;
        els.currentImageReviewSection.style.display = "block";
      } else {
        els.currentImageReviewSection.style.display = "none";
        els.currentImageReviewThumb.src = "";
      }

      els.reviewSubmitBtn.disabled = false;
      els.reviewSubmitBtn.textContent = "Save Review & Image"; // Reset button text
      els.reviewImageForm.action = `/places/${placeData.id}/review-image`; // Set correct action

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
    if (this.elements.reviewImageSection)
      this.elements.reviewImageSection.style.display = "none";
    this.currentPlaceDataForReview = null;
    // Restore "Add New Place" button text if add form is also hidden
    if (
      !this.elements.addPlaceWrapper ||
      this.elements.addPlaceWrapper.style.display === "none"
    ) {
      if (this.elements.toggleAddPlaceBtn)
        this.elements.toggleAddPlaceBtn.textContent = "Add New Place";
    }
  },

  showSeeReviewModal(placeDataInput) {
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

    this.currentPlaceDataForReview = placeData; // Store data for the edit button
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

      // Handle image display
      if (els.seeReviewDisplayImage) {
        if (placeData.image_url && placeData.image_url.startsWith("http")) {
          els.seeReviewDisplayImage.src = placeData.image_url;
          els.seeReviewDisplayImage.alt = `Image for ${
            placeData.name || "place"
          }`;
          els.seeReviewDisplayImage.style.display = "block";
          // Ensure click listener is attached (or re-attached)
          // els.seeReviewDisplayImage.onclick = this.showImageOverlay.bind(this); // Handled by delegation now
        } else {
          els.seeReviewDisplayImage.style.display = "none";
          els.seeReviewDisplayImage.src = "";
          // els.seeReviewDisplayImage.onclick = null;
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
    if (this.elements.seeReviewSection)
      this.elements.seeReviewSection.style.display = "none";
    this.currentPlaceDataForReview = null;
    // if (this.elements.seeReviewDisplayImage) this.elements.seeReviewDisplayImage.onclick = null; // Handled by delegation now
    // Restore "Add New Place" button text if add form is also hidden
    if (
      !this.elements.addPlaceWrapper ||
      this.elements.addPlaceWrapper.style.display === "none"
    ) {
      if (this.elements.toggleAddPlaceBtn)
        this.elements.toggleAddPlaceBtn.textContent = "Add New Place";
    }
  },

  // --- Geocoding ---
  async handleGeocodeRequest(formType = "add") {
    console.log(`UI: Geocode request for form type: ${formType}`);
    mapHandler.stopPinningMode(); // Stop pinning if active

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
      console.error(
        `Geocode Error: Missing elements for form type '${formType}'.`
      );
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
    submitButton.disabled = true; // Disable submit while geocoding

    try {
      // Use apiClient for the geocode request
      const geocodeUrl = `/api/v1/geocode?address=${encodeURIComponent(
        addressQuery
      )}`;
      const response = await apiClient.get(geocodeUrl); // Use GET helper

      if (response.ok) {
        const result = await response.json();
        this.updateCoordsDisplay(result, formType); // Update UI fields
        this.setStatusMessage(
          statusEl,
          `Location found: ${result.display_name}`,
          "success"
        );
        // Fly map to the location
        mapHandler.flyTo(result.latitude, result.longitude);
      } else {
        let errorDetail = `Geocoding failed (${response.status}).`;
        try {
          const errorData = await response.json();
          errorDetail = errorData.detail || errorDetail;
        } catch (e) {
          /* ignore if response not json */
        }
        this.setStatusMessage(statusEl, `Error: ${errorDetail}`, "error");
      }
    } catch (error) {
      // apiClient handles 401 redirect, catch other errors
      console.error("Geocoding fetch error:", error);
      this.setStatusMessage(
        statusEl,
        "Network error or server issue during geocoding.",
        "error"
      );
    } finally {
      if (findBtn) findBtn.disabled = false;
      // Re-enable submit button ONLY if coordinates are now valid
      const latVal = isEdit
        ? this.elements.editLatitudeInput.value
        : this.elements.addHiddenLat.value;
      const lonVal = isEdit
        ? this.elements.editLongitudeInput.value
        : this.elements.addHiddenLon.value;
      if (submitButton) submitButton.disabled = !(latVal && lonVal);
    }
  },

  /**
   * Updates coordinate display fields based on geocoding result or map pin.
   * @param {object} coordsData - Object like { latitude, longitude, address?, city?, country?, display_name? }.
   * @param {string} formType - 'add' or 'edit'.
   */
  updateCoordsDisplay(coordsData, formType = "add") {
    const isEdit = formType === "edit";
    const els = this.elements;
    const coordsSect = isEdit ? els.editCoordsSection : els.addCoordsSection;
    const dispLatEl = isEdit ? els.editDisplayLat : els.addDisplayLat;
    const dispLonEl = isEdit ? els.editDisplayLon : els.addDisplayLon;
    const dispAddrEl = isEdit ? null : els.addDisplayAddress; // Only add form has display address field
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
      coordsSect.style.display = "none"; // Hide if invalid
      return;
    }

    // Update hidden inputs
    latInput.value = lat;
    lonInput.value = lon;
    // Update address parts ONLY if they came from geocoding (not from map pin)
    // A map pin might not have address details.
    if (
      coordsData.display_name !== undefined ||
      coordsData.address !== undefined
    ) {
      addrHidden.value = coordsData.address || ""; // Store street address if available
      cityHidden.value = coordsData.city || "";
      countryHidden.value = coordsData.country || "";
    } else {
      // If only lat/lon provided (from map pin), clear address fields? Or keep previous geocoded ones?
      // Let's keep previous ones for now, user can re-geocode if needed.
      // addrHidden.value = "";
      // cityHidden.value = "";
      // countryHidden.value = "";
    }

    // Update display elements
    dispLatEl.textContent = lat.toFixed(6);
    dispLonEl.textContent = lon.toFixed(6);
    if (dispAddrEl) {
      // Only for add form
      dispAddrEl.textContent =
        coordsData.display_name || "(Coordinates set manually)";
    }

    coordsSect.style.display = "block";
    submitButton.disabled = false; // Enable submit now that coords are valid
  },

  // --- Map Pinning Control ---
  /**
   * Toggles map pinning mode for the specified form.
   * @param {string} formType - 'add' or 'edit'.
   */
  toggleMapPinning(formType = "add") {
    // Check if mapHandler is trying to *stop* pinning for this form type
    if (
      mapHandler.isPinningModeActive &&
      mapHandler.currentPinningFormType === formType
    ) {
      mapHandler.stopPinningMode();
    } else {
      // If switching modes, stop the other one first
      if (
        mapHandler.isPinningModeActive &&
        mapHandler.currentPinningFormType !== formType
      ) {
        mapHandler.stopPinningMode();
      }
      // Start pinning for the requested form type
      let initialCoords = null;
      if (formType === "edit") {
        const lat = parseFloat(this.elements.editLatitudeInput?.value);
        const lng = parseFloat(this.elements.editLongitudeInput?.value);
        if (!isNaN(lat) && !isNaN(lng)) {
          initialCoords = { lat, lng };
        }
      }
      mapHandler.startPinningMode(formType, initialCoords);
    }
  },

  /**
   * Callback function called by mapHandler when pinning mode changes.
   * Updates the UI elements (buttons, instructions).
   * @param {boolean} isActive - Whether pinning mode is now active.
   * @param {string} formType - The form type ('add' or 'edit') affected.
   */
  handlePinningModeChange(isActive, formType) {
    console.debug(
      `UI: Pinning mode changed to ${isActive} for form '${formType}'`
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

    if (isActive) {
      if (addressInput) addressInput.disabled = true;
      if (findBtn) findBtn.disabled = true;
      if (instructionEl) instructionEl.style.display = "block";
      if (pinBtn) pinBtn.textContent = "Cancel Pinning";
      this.setStatusMessage(
        statusEl,
        "Click the map to set the location.",
        "info"
      );
    } else {
      if (addressInput) addressInput.disabled = false;
      if (findBtn) findBtn.disabled = false;
      if (instructionEl) instructionEl.style.display = "none";
      if (pinBtn) pinBtn.textContent = "Pin Location on Map";
      // Don't clear status message here, might contain success from pinning
      // Check if coords are valid to enable submit button
      const latInput = isEdit
        ? this.elements.editLatitudeInput
        : this.elements.addHiddenLat;
      const lonInput = isEdit
        ? this.elements.editLongitudeInput
        : this.elements.addHiddenLon;
      const submitBtn = isEdit
        ? this.elements.editSubmitBtn
        : this.elements.addSubmitBtn;
      if (submitBtn) {
        submitBtn.disabled = !(latInput?.value && lonInput?.value);
      }
    }
  },

  /**
   * Callback function called by mapHandler when coordinates are updated via map pin/drag.
   * @param {object} coords - Object with { latitude, longitude }.
   * @param {string} formType - The form type ('add' or 'edit') these coords are for.
   */
  handleCoordsUpdateFromMap(coords, formType) {
    console.debug(
      `UI: Received coords update from map for form '${formType}':`,
      coords
    );
    const statusEl =
      formType === "edit"
        ? this.elements.editGeocodeStatus
        : this.elements.addGeocodeStatus;
    const addressInput =
      formType === "edit"
        ? this.elements.editAddressInput
        : this.elements.addAddressInput;

    // Update the display and hidden inputs
    this.updateCoordsDisplay(coords, formType);
    // Update status message and clear address input
    this.setStatusMessage(statusEl, "Location updated via map.", "success");
    if (addressInput) addressInput.value = ""; // Clear address field after pinning
  },

  // --- Rating Stars ---
  setupRatingStars() {
    this.setupInteractiveStars(
      this.elements.reviewRatingStarsContainer,
      this.elements.reviewRatingInput
    );
    this.setupInteractiveStars(
      this.elements.editRatingStarsContainer,
      this.elements.editRatingInput
    );
  },

  setupInteractiveStars(containerElement, hiddenInputElement) {
    if (!containerElement || !hiddenInputElement) return;
    const stars = containerElement.querySelectorAll(".star");

    stars.forEach((star) => {
      star.addEventListener("click", (event) => {
        event.stopPropagation(); // Prevent potential parent clicks
        const value = star.getAttribute("data-value");
        hiddenInputElement.value = value; // Update hidden input
        this.updateRatingStars(containerElement, value); // Update visual selection
      });
      star.addEventListener("mouseover", () => {
        const value = star.getAttribute("data-value");
        this.highlightStars(containerElement, value); // Highlight on hover
      });
      star.addEventListener("mouseout", () => {
        // Restore visual state based on hidden input value
        this.updateRatingStars(containerElement, hiddenInputElement.value);
      });
    });
    // Initial visual state based on hidden input (e.g., when editing)
    this.updateRatingStars(containerElement, hiddenInputElement.value);
  },

  highlightStars(containerElement, value) {
    if (!containerElement) return;
    const stars = containerElement.querySelectorAll(".star");
    const ratingValue = parseInt(value, 10);
    stars.forEach((star) => {
      const starValue = parseInt(star.getAttribute("data-value"), 10);
      const icon = star.querySelector("i");
      if (!icon) return;
      if (starValue <= ratingValue) {
        icon.classList.remove("far"); // Empty star
        icon.classList.add("fas"); // Full star
        star.classList.add("selected");
      } else {
        icon.classList.remove("fas");
        icon.classList.add("far");
        star.classList.remove("selected");
      }
    });
  },

  updateRatingStars(containerElement, selectedValue) {
    if (!containerElement) return;
    const currentRating = parseInt(selectedValue, 10) || 0; // Default to 0 if null/invalid
    this.highlightStars(containerElement, currentRating);
  },

  displayStaticRatingStars(containerElement, rating) {
    if (!containerElement) return;
    const numericRating = parseInt(rating, 10);
    if (numericRating && numericRating >= 1 && numericRating <= 5) {
      let starsHtml = "";
      for (let i = 1; i <= 5; i++) {
        starsHtml += `<i class="${
          i <= numericRating ? "fas" : "far"
        } fa-star"></i> `;
      }
      containerElement.innerHTML = starsHtml.trim();
      containerElement.style.display = "inline-block"; // Make visible
    } else {
      containerElement.innerHTML = "(No rating)";
      containerElement.style.display = "inline-block"; // Show placeholder
    }
  },

  // --- Utility Functions ---
  setStatusMessage(element, message, type = "info") {
    if (!element) {
      // console.warn("Attempted to set status message on null element:", message);
      return;
    }
    element.textContent = message;
    element.className = "status-message"; // Reset classes first
    if (type === "error") element.classList.add("error-message");
    else if (type === "success") element.classList.add("success-message");
    else if (type === "loading") element.classList.add("loading-indicator");
    else element.classList.add("info-message"); // Default to info style if needed

    element.style.display = message ? "block" : "none";
  },

  resetAddPlaceForm() {
    if (this.elements.addPlaceForm) this.elements.addPlaceForm.reset();
    // Reset coordinates section specifically
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
    // Reset pinning button state
    if (this.elements.addPinOnMapBtn)
      this.elements.addPinOnMapBtn.textContent = "Pin Location on Map";
    if (this.elements.addMapPinInstruction)
      this.elements.addMapPinInstruction.style.display = "none";
    if (this.elements.addAddressInput)
      this.elements.addAddressInput.disabled = false;
    if (this.elements.addFindCoordsBtn)
      this.elements.addFindCoordsBtn.disabled = false;
  },

  // --- Image Overlay ---
  showImageOverlay(event) {
    const clickedImage = event.target;
    // Check if the clicked element is an image with a valid src
    if (
      !clickedImage ||
      clickedImage.tagName !== "IMG" ||
      !clickedImage.src ||
      !clickedImage.src.startsWith("http")
    ) {
      console.debug("Image overlay click ignored - not a valid image source.");
      return;
    }

    let overlay = document.querySelector(".image-overlay");
    if (!overlay) {
      overlay = document.createElement("div");
      overlay.className = "image-overlay";
      const imageInOverlay = document.createElement("img");
      imageInOverlay.alt = clickedImage.alt || "Enlarged image";
      // Prevent clicks on the image itself from closing the overlay
      imageInOverlay.onclick = function (e) {
        e.stopPropagation();
      };
      overlay.appendChild(imageInOverlay);
      // Click on the background closes the overlay
      overlay.onclick = this.hideImageOverlay.bind(this);
      document.body.appendChild(overlay);
    }

    const imageInOverlay = overlay.querySelector("img");
    if (imageInOverlay) imageInOverlay.src = clickedImage.src; // Set the source for the overlay image

    // Use setTimeout to allow the element to be added to DOM before adding class for transition
    setTimeout(() => overlay.classList.add("visible"), 10);
  },

  hideImageOverlay() {
    const overlay = document.querySelector(".image-overlay.visible");
    if (overlay) {
      overlay.classList.remove("visible");
      // Remove the overlay from DOM after transition ends for cleanup
      overlay.addEventListener(
        "transitionend",
        () => {
          if (document.body.contains(overlay)) {
            // Check if still exists
            document.body.removeChild(overlay);
          }
        },
        { once: true }
      );
    }
  },
};

export default ui;
