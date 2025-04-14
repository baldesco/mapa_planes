/**
 * uiOrchestrator.js
 * Handles the high-level orchestration of UI sections (Add/Edit/Review forms, Modals)
 * on the main page, and initializes specific form/component modules.
 */

import addPlaceForm from "./forms/addPlaceForm.js";
import editPlaceForm from "./forms/editPlaceForm.js";
import reviewForm from "./forms/reviewForm.js";
import modals from "./components/modals.js";
import pinningUI from "./components/pinningUI.js";
import mapHandler from "./mapHandler.js";
import tagInput from "./components/tagInput.js";

function debounce(func, wait) {
  let timeout;
  return function executedFunction(...args) {
    const later = () => {
      clearTimeout(timeout);
      func(...args);
    };
    clearTimeout(timeout);
    timeout = setTimeout(later, wait);
  };
}

const uiOrchestrator = {
  elements: {
    // Main section wrappers
    toggleAddPlaceBtn: null,
    addPlaceWrapper: null,
    editPlaceSection: null,
    reviewImageSection: null,
    seeReviewSection: null,
    // Map container
    mapContainer: null,
    mapIframe: null,
    // Pinning map container
    pinningMapContainer: null,
    // Tag inputs
    tagFilterInput: null,
    editTagsInput: null,
  },
  isMapReady: false,
  debouncedInvalidateMapSize: null,
  allUserTags: [], // Store all tags for suggestions

  init(mapReadyStatus = false) {
    console.debug("UI Orchestrator: Initializing...");
    this.isMapReady = mapReadyStatus;
    this.cacheDOMElements(); // Cache elements including iframe
    this.loadUserTags(); // Load tags from embedded data
    this.hideAllSections();

    // Initialize sub-modules
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
    modals.init(this.showReviewForm.bind(this));
    pinningUI.init(this.isMapReady);

    // Initialize Tagify components
    if (this.elements.tagFilterInput) {
      tagInput.init("tag-filter-input", this.allUserTags, {
        editTags: false,
        placeholder: "Filter by tags...",
        hooks: {
          add: [
            () => {
              console.debug("Filter tag added");
              document.getElementById("filter-form")?.submit();
            },
          ],
          remove: [
            () => {
              console.debug("Filter tag removed");
              document.getElementById("filter-form")?.submit();
            },
          ],
        },
      });
    }

    this.setupEventListeners();

    // Make global functions available on the parent window
    window.attachMapClickListener = this.attachMapClickListener.bind(this);
    window.isPinningActive = () => pinningUI.isActive; // Check pinning state
    window.handleMapPinClick = this.handleMapPinClick.bind(this); // Handle click event during pinning
    window.showEditPlaceForm = this.showEditPlaceForm.bind(this);
    window.showReviewForm = this.showReviewForm.bind(this);
    window.showSeeReviewModal = modals.showSeeReviewModal.bind(modals);
    window.showImageOverlay = modals.showImageOverlay.bind(modals);

    // Setup Resize Observer
    if (this.isMapReady && this.elements.mapContainer) {
      this.setupResizeObserver();
    } else if (!this.elements.mapContainer) {
      console.warn(
        "UI Orchestrator: #map container not found for ResizeObserver."
      );
    }

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
    this.elements.mapContainer = document.getElementById("map");
    // Try to find the iframe within the map container
    if (this.elements.mapContainer) {
      // Use a more robust selector if the structure changes
      this.elements.mapIframe =
        this.elements.mapContainer.querySelector("iframe");
      if (!this.elements.mapIframe) {
        console.warn(
          "UI Orchestrator: Could not find iframe inside #map container."
        );
      }
    }
    this.elements.pinningMapContainer = document.getElementById(
      "pinning-map-container"
    );
    this.elements.tagFilterInput = document.getElementById("tag-filter-input");
    this.elements.editTagsInput = document.getElementById("edit-tags-input");
  },

  loadUserTags() {
    const tagsDataElement = document.getElementById("user-tags-data");
    if (tagsDataElement) {
      try {
        const tagsData = JSON.parse(tagsDataElement.textContent || "[]");
        this.allUserTags = tagsData.map((tag) => tag.name);
        console.log(
          `Loaded ${this.allUserTags.length} user tags for suggestions.`
        );
      } catch (e) {
        console.error("Failed to parse embedded user tags data:", e);
        this.allUserTags = [];
      }
    } else {
      console.warn("User tags data element not found.");
      this.allUserTags = [];
    }
  },

  setupEventListeners() {
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

  setupResizeObserver() {
    if (!this.elements.mapContainer) return;
    this.debouncedInvalidateMapSize = debounce(
      mapHandler.invalidateMapSize.bind(mapHandler),
      250
    );
    const resizeObserver = new ResizeObserver((entries) => {
      for (let entry of entries) {
        this.debouncedInvalidateMapSize();
      }
    });
    resizeObserver.observe(this.elements.mapContainer);
    console.log("UI Orchestrator: ResizeObserver attached to #map container.");
  },

  /**
   * Attaches the click listener to the Leaflet map inside the iframe.
   * Called by the script injected from mapping.py.
   * @param {string} mapVarName - The JavaScript variable name of the map instance inside the iframe.
   */
  attachMapClickListener(mapVarName) {
    console.debug(
      `UI Orchestrator: Received request to attach listener to map var '${mapVarName}'`
    );
    if (!this.elements.mapIframe || !this.elements.mapIframe.contentWindow) {
      console.error(
        "Cannot attach listener: Map iframe or its contentWindow not found."
      );
      // Attempt to find iframe again if caching failed initially
      if (this.elements.mapContainer) {
        this.elements.mapIframe =
          this.elements.mapContainer.querySelector("iframe");
        if (
          !this.elements.mapIframe ||
          !this.elements.mapIframe.contentWindow
        ) {
          console.error(
            "Still cannot find iframe or contentWindow after re-check."
          );
          return;
        }
        console.log("Found iframe on second attempt.");
      } else {
        return; // Give up if map container isn't even cached
      }
    }

    const iframeWindow = this.elements.mapIframe.contentWindow;

    // Function to perform the attachment
    const tryAttach = () => {
      try {
        // Access the map instance using window[varName] inside the iframe's context
        const mapInstance = iframeWindow[mapVarName];
        if (mapInstance && typeof mapInstance.on === "function") {
          console.log(
            `Attaching click listener to map '${mapVarName}' in iframe.`
          );
          // Define the listener function *here* in the parent scope
          const listener = (e) => {
            // Use the globally exposed function to check pinning state
            if (window.isPinningActive()) {
              console.log(
                "Parent Script (Map Event): Map clicked while pinning active. Lat:",
                e.latlng.lat,
                "Lng:",
                e.latlng.lng
              );
              // Use the globally exposed handler
              window.handleMapPinClick(e.latlng.lat, e.latlng.lng);
            }
          };
          // Remove previous listener if any? Might not be necessary if instance is recreated.
          // mapInstance.off('click', listener); // Be careful with listener references
          mapInstance.on("click", listener);
          return true; // Indicate success
        } else {
          console.warn(
            `Map instance '${mapVarName}' not found or not ready in iframe yet.`
          );
          return false; // Indicate failure
        }
      } catch (err) {
        console.error(
          `Error attaching map click listener to '${mapVarName}':`,
          err
        );
        return false; // Indicate failure
      }
    };

    // Try immediately, and retry if it fails initially
    if (!tryAttach()) {
      console.log("Retrying listener attachment after delay...");
      setTimeout(() => {
        if (!tryAttach()) {
          console.error(
            `Failed to attach listener to '${mapVarName}' even after delay.`
          );
        }
      }, 1500); // Increase delay further
    }
  },

  /**
   * Handles the map click event when pinning is active.
   * Called by the listener attached in attachMapClickListener.
   * @param {number} lat - Latitude of the click.
   * @param {number} lng - Longitude of the click.
   */
  handleMapPinClick(lat, lng) {
    // Use pinningUI directly as it holds the state and callback
    if (!pinningUI.isActive || !pinningUI.updateCoordsCallback) {
      console.warn(
        "handleMapPinClick called but pinning not active or callback missing."
      );
      return;
    }
    console.log(
      `Handling map pin click at [${lat}, ${lng}] for form: ${pinningUI.activeFormType}`
    );
    // Update the coordinates display/hidden inputs on the active form
    pinningUI.updateCoordsCallback({ latitude: lat, longitude: lng });
    // Deactivate pinning after click? Let's keep the confirm button workflow for now.
  },

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

    pinningUI.deactivatePinning();

    if (this.elements.pinningMapContainer) {
      this.elements.pinningMapContainer.style.display = "none";
    }

    if (this.elements.toggleAddPlaceBtn) {
      this.elements.toggleAddPlaceBtn.textContent = "Add New Place";
    }
    tagInput.destroy("edit-tags-input");
  },

  // --- Show/Hide Methods ---
  // (No changes needed in show/hide methods)
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
    if (typeof placeDataInput === "string") {
      try {
        placeData = JSON.parse(placeDataInput);
      } catch (e) {
        console.error(
          "UI Orchestrator: Failed to parse placeData JSON for edit form:",
          e
        );
        alert("Error: Could not read place data to edit.");
        return;
      }
    } else if (typeof placeDataInput === "object" && placeDataInput !== null) {
      placeData = placeDataInput;
    } else {
      console.error(
        "UI Orchestrator: Invalid data type received for edit form:",
        placeDataInput
      );
      alert("Internal Error: Invalid data for edit form.");
      return;
    }
    this.hideAllSections();
    if (editPlaceForm.populateForm(placeData)) {
      if (this.elements.editPlaceSection) {
        this.elements.editPlaceSection.style.display = "block";
        if (this.elements.toggleAddPlaceBtn)
          this.elements.toggleAddPlaceBtn.textContent = "Add New Place";
        if (this.elements.editTagsInput) {
          tagInput.init("edit-tags-input", this.allUserTags, {
            placeholder: "Add tags...",
          });
          tagInput.setTags("edit-tags-input", placeData.tags || []);
        }
        this.elements.editPlaceSection.scrollIntoView({
          behavior: "smooth",
          block: "start",
        });
      }
    } else {
      console.error("UI Orchestrator: Failed to populate edit form.");
    }
  },
  hideEditPlaceForm() {
    if (this.elements.editPlaceSection)
      this.elements.editPlaceSection.style.display = "none";
    if (this.elements.toggleAddPlaceBtn)
      this.elements.toggleAddPlaceBtn.textContent = "Add New Place";
    pinningUI.deactivateIfActiveFor("edit");
    tagInput.destroy("edit-tags-input");
  },
  showReviewForm(placeDataInput) {
    let placeData;
    if (typeof placeDataInput === "string") {
      try {
        placeData = JSON.parse(placeDataInput);
      } catch (e) {
        console.error(
          "UI Orchestrator: Failed to parse placeData JSON for review form:",
          e
        );
        alert("Error: Could not read place data for review.");
        return;
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
};

export default uiOrchestrator;
