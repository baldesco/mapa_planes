/**
 * reviewForm.js
 * Manages interactions and state for the Add/Edit Review & Image form.
 */

const reviewForm = {
  elements: {
    form: null,
    wrapper: null,
    cancelBtn: null,
    formTitle: null,
    titleInput: null,
    textInput: null,
    ratingStarsContainer: null,
    ratingInput: null, // Hidden input for rating value
    imageInput: null,
    removeImageCheckbox: null,
    currentImageSection: null,
    currentImageThumb: null,
    submitBtn: null,
  },
  hideCallback: null, // Function provided by orchestrator to hide this form
  currentPlaceData: null, // Store data of the place being reviewed

  init(showFn, hideFn) {
    console.debug("Review Form: Initializing...");
    this.hideCallback = hideFn;
    this.cacheDOMElements();
    this.setupEventListeners();
    this.setupRatingStars(); // Initialize interactive stars
  },

  cacheDOMElements() {
    this.elements.wrapper = document.getElementById("review-image-section");
    if (!this.elements.wrapper) return;

    this.elements.form = document.getElementById("review-image-form");
    this.elements.cancelBtn =
      this.elements.wrapper.querySelector("button.cancel-btn");
    this.elements.formTitle = document.getElementById("review-form-title");
    this.elements.titleInput = document.getElementById("review-title");
    this.elements.textInput = document.getElementById("review-text");
    this.elements.ratingStarsContainer = document.getElementById(
      "review-rating-stars"
    );
    this.elements.ratingInput = document.getElementById("review-rating");
    this.elements.imageInput = document.getElementById("review-image");
    this.elements.removeImageCheckbox = document.getElementById(
      "review-remove-image"
    );
    this.elements.currentImageSection = document.getElementById(
      "current-image-review-section"
    );
    this.elements.currentImageThumb = document.getElementById(
      "current-image-review-thumb"
    );
    this.elements.submitBtn = document.getElementById(
      "review-image-submit-btn"
    );
  },

  setupEventListeners() {
    if (!this.elements.form) return;

    if (this.elements.cancelBtn && this.hideCallback) {
      this.elements.cancelBtn.addEventListener("click", () =>
        this.hideCallback()
      );
    }

    // Optional: Add listener to clear file input if remove checkbox is checked?
    if (this.elements.removeImageCheckbox && this.elements.imageInput) {
      this.elements.removeImageCheckbox.addEventListener("change", (event) => {
        if (event.target.checked) {
          this.elements.imageInput.value = ""; // Clear file selection if removing
        }
      });
    }
    // Optional: Uncheck remove checkbox if a new file is selected
    if (this.elements.imageInput && this.elements.removeImageCheckbox) {
      this.elements.imageInput.addEventListener("change", (event) => {
        if (event.target.files && event.target.files.length > 0) {
          this.elements.removeImageCheckbox.checked = false;
        }
      });
    }

    // Form submission is handled by uiOrchestrator's setupFormSubmission
  },

  /** Populates the form with data for the place being reviewed/edited */
  populateForm(placeData) {
    if (!this.elements.form) {
      console.error("Review form elements not cached.");
      return false;
    }
    if (!placeData || typeof placeData !== "object") {
      console.error("Invalid placeData provided to populateForm:", placeData);
      return false;
    }

    this.currentPlaceData = placeData;
    const els = this.elements;

    try {
      els.formTitle.textContent = `"${placeData.name || "Unknown"}"`;
      els.titleInput.value = placeData.review_title || "";
      els.textInput.value = placeData.review || "";

      // Handle rating (expecting null or number, store as string or "")
      const currentRating =
        placeData.rating !== null && placeData.rating !== undefined
          ? String(placeData.rating)
          : "";
      els.ratingInput.value = currentRating;
      this.updateRatingStars(els.ratingStarsContainer, currentRating); // Update visual stars

      // Reset file input and checkbox
      els.imageInput.value = "";
      els.removeImageCheckbox.checked = false;

      // Show current image preview if available
      if (placeData.image_url && placeData.image_url.startsWith("http")) {
        if (els.currentImageThumb)
          els.currentImageThumb.src = placeData.image_url;
        if (els.currentImageSection)
          els.currentImageSection.style.display = "block";
      } else {
        if (els.currentImageSection)
          els.currentImageSection.style.display = "none";
        if (els.currentImageThumb) els.currentImageThumb.src = "";
      }

      // Reset submit button and set form action
      els.submitBtn.disabled = false;
      els.submitBtn.textContent = "Save Review & Image";
      els.form.action = `/places/${placeData.id}/review-image`;

      return true; // Indicate success
    } catch (e) {
      console.error("Error populating review form fields:", e);
      this.currentPlaceData = null;
      return false; // Indicate failure
    }
  },

  // --- Rating Stars Logic ---
  // (Copied from the original ui.js, now encapsulated here)
  setupRatingStars() {
    this.setupInteractiveStars(
      this.elements.ratingStarsContainer,
      this.elements.ratingInput
    );
  },
  setupInteractiveStars(container, hiddenInput) {
    if (!container || !hiddenInput) return;
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
    this.updateRatingStars(container, hiddenInput.value); // Initial setup
  },
  highlightStars(container, value) {
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
    if (!container) return;
    this.highlightStars(container, parseInt(selectedValue, 10) || 0);
  },
  // --- End Rating Stars Logic ---
};

export default reviewForm;
