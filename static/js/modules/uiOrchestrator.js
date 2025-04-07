/**
 * uiOrchestrator.js
 * Handles the high-level orchestration of UI sections (Add/Edit/Review forms, Modals)
 * on the main page, and initializes specific form/component modules.
 */

import addPlaceForm from "./forms/addPlaceForm.js";
import editPlaceForm from "./forms/editPlaceForm.js";
import reviewForm from "./forms/reviewForm.js";
import modals from "./components/modals.js";
import pinningUI from "./components/pinningUI.js"; // Import pinning UI handler

const uiOrchestrator = {
  elements: {
    // Main section wrappers
    toggleAddPlaceBtn: null,
    addPlaceWrapper: null,
    editPlaceSection: null,
    reviewImageSection: null,
    seeReviewSection: null,
    // Pinning map container (needed to ensure it's hidden initially)
    pinningMapContainer: null,
  },
  isMapReady: false, // Track if the main map initialized successfully

  init(mapReadyStatus = false) {
    console.debug("UI Orchestrator: Initializing...");
    this.isMapReady = mapReadyStatus;
    this.cacheDOMElements();
    this.hideAllSections(); // Ensure clean initial state

    // Initialize sub-modules that handle specific UI parts
    addPlaceForm.init(
      this.isMapReady,
      this.showAddPlaceForm.bind(this),
      this.hideAddPlaceForm.bind(this)
    );
    editPlaceForm.init(
      this.isMapReady,
      this.showEditPlaceForm.bind(this),
      this.hideEditPlaceForm.bind(this)
    );
    reviewForm.init(
      this.showReviewForm.bind(this),
      this.hideReviewForm.bind(this)
    );
    modals.init(this.showReviewForm.bind(this)); // Pass showReviewForm for the "Edit" button in SeeReview modal
    pinningUI.init(this.isMapReady); // Initialize pinning UI handler

    this.setupEventListeners();

    // Make global functions available (called from map popups)
    // window.showAddPlaceForm = this.showAddPlaceForm.bind(this); // Should ideally not be needed
    window.showEditPlaceForm = this.showEditPlaceForm.bind(this);
    window.showReviewForm = this.showReviewForm.bind(this);
    window.showSeeReviewModal = modals.showSeeReviewModal.bind(modals);
    window.showImageOverlay = modals.showImageOverlay.bind(modals);

    console.log("UI Orchestrator: Initialization complete.");
  },

  cacheDOMElements() {
    this.elements.toggleAddPlaceBtn = document.getElementById(
      "toggle-add-place-form-btn"
    );
    this.elements.addPlaceWrapper = document.getElementById(
      "add-place-wrapper-section"
    );
    this.elements.editPlaceSection =
      document.getElementById("edit-place-section");
    this.elements.reviewImageSection = document.getElementById(
      "review-image-section"
    );
    this.elements.seeReviewSection =
      document.getElementById("see-review-section");
    this.elements.pinningMapContainer = document.getElementById(
      "pinning-map-container"
    );
  },

  setupEventListeners() {
    // Toggle Add Place Form Button
    if (this.elements.toggleAddPlaceBtn) {
      this.elements.toggleAddPlaceBtn.addEventListener("click", () => {
        const isHidden =
          !this.elements.addPlaceWrapper ||
          this.elements.addPlaceWrapper.style.display === "none" ||
          this.elements.addPlaceWrapper.style.display === "";
        if (isHidden) {
          this.showAddPlaceForm();
        } else {
          this.hideAddPlaceForm();
        }
      });
    }
  },

  /** Hides all major form/modal sections and resets pinning */
  hideAllSections() {
    console.debug("UI Orchestrator: Hiding all sections.");
    if (this.elements.addPlaceWrapper)
      this.elements.addPlaceWrapper.style.display = "none";
    if (this.elements.editPlaceSection)
      this.elements.editPlaceSection.style.display = "none";
    if (this.elements.reviewImageSection)
      this.elements.reviewImageSection.style.display = "none";
    if (this.elements.seeReviewSection)
      this.elements.seeReviewSection.style.display = "none";

    pinningUI.deactivatePinning(); // Reset pinning UI if active

    if (this.elements.pinningMapContainer) {
      this.elements.pinningMapContainer.style.display = "none";
    }

    if (this.elements.toggleAddPlaceBtn) {
      this.elements.toggleAddPlaceBtn.textContent = "Add New Place";
    }
  },

  // --- Show/Hide Methods for Main Sections ---

  showAddPlaceForm() {
    this.hideAllSections();
    addPlaceForm.resetForm();
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
    pinningUI.deactivateIfActiveFor("add");
  },

  showEditPlaceForm(placeDataInput) {
    let placeData;
    // *** FIX: Parse the incoming string data ***
    if (typeof placeDataInput === "string") {
      try {
        placeData = JSON.parse(placeDataInput);
      } catch (e) {
        console.error(
          "UI Orchestrator: Failed to parse placeData JSON for edit form:",
          e,
          "Input:",
          placeDataInput
        );
        alert("Error: Could not read place data to edit.");
        return; // Stop if parsing fails
      }
    } else if (typeof placeDataInput === "object" && placeDataInput !== null) {
      // Allow passing object directly (though popups pass strings)
      placeData = placeDataInput;
    } else {
      console.error(
        "UI Orchestrator: Invalid data type received for edit form:",
        placeDataInput
      );
      alert("Internal Error: Invalid data for edit form.");
      return;
    }
    // *** END FIX ***

    this.hideAllSections(); // Hide other sections first

    // Now call populateForm with the actual object
    if (editPlaceForm.populateForm(placeData)) {
      if (this.elements.editPlaceSection) {
        this.elements.editPlaceSection.style.display = "block";
        if (this.elements.toggleAddPlaceBtn)
          this.elements.toggleAddPlaceBtn.textContent = "Add New Place";
        this.elements.editPlaceSection.scrollIntoView({
          behavior: "smooth",
          block: "start",
        });
      }
    } else {
      console.error("UI Orchestrator: Failed to populate edit form.");
      // Optionally show an error message to the user
    }
  },

  hideEditPlaceForm() {
    if (this.elements.editPlaceSection)
      this.elements.editPlaceSection.style.display = "none";
    if (this.elements.toggleAddPlaceBtn)
      this.elements.toggleAddPlaceBtn.textContent = "Add New Place";
    pinningUI.deactivateIfActiveFor("edit");
  },

  showReviewForm(placeDataInput) {
    let placeData;
    // *** FIX: Parse the incoming string data ***
    if (typeof placeDataInput === "string") {
      try {
        placeData = JSON.parse(placeDataInput);
      } catch (e) {
        console.error(
          "UI Orchestrator: Failed to parse placeData JSON for review form:",
          e,
          "Input:",
          placeDataInput
        );
        alert("Error: Could not read place data for review.");
        return; // Stop if parsing fails
      }
    } else if (typeof placeDataInput === "object" && placeDataInput !== null) {
      placeData = placeDataInput;
    } else {
      console.error(
        "UI Orchestrator: Invalid data type received for review form:",
        placeDataInput
      );
      alert("Internal Error: Invalid data for review form.");
      return;
    }
    // *** END FIX ***

    this.hideAllSections();

    if (reviewForm.populateForm(placeData)) {
      if (this.elements.reviewImageSection) {
        this.elements.reviewImageSection.style.display = "block";
        if (this.elements.toggleAddPlaceBtn)
          this.elements.toggleAddPlaceBtn.textContent = "Add New Place";
        this.elements.reviewImageSection.scrollIntoView({
          behavior: "smooth",
          block: "start",
        });
      }
    } else {
      console.error("UI Orchestrator: Failed to populate review form.");
    }
  },

  hideReviewForm() {
    if (this.elements.reviewImageSection)
      this.elements.reviewImageSection.style.display = "none";
    if (this.elements.toggleAddPlaceBtn)
      this.elements.toggleAddPlaceBtn.textContent = "Add New Place";
  },

  // Note: showSeeReviewModal and showImageOverlay are delegated to modals.js
};

export default uiOrchestrator;
