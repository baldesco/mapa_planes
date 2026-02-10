/**
 * reviewForm.js
 * Manages interactions and state for the Add/Edit Review & Image form for a visit.
 * Updated for SPA-Lite behavior to update the map without reloading.
 */
import apiClient from "../apiClient.js";
import { setStatusMessage } from "../components/statusMessages.js";

const reviewForm = {
  elements: {
    wrapper: null,
    form: null,
    formTitlePlaceSpan: null,
    visitDateTimeSpan: null,
    visitIdInput: null,
    titleInput: null,
    textInput: null,
    ratingStarsContainer: null,
    ratingInput: null,
    imageInput: null,
    removeImageCheckbox: null,
    currentImageSection: null,
    currentImageThumb: null,
    statusMessage: null,
    submitBtn: null,
    cancelBtn: null,
  },
  hideCallback: null,
  onReviewSavedCallback: null,
  currentVisitData: null,
  currentPlaceName: null,

  init(hideFn, onSaveFn) {
    this.hideCallback = hideFn;
    this.onReviewSavedCallback = onSaveFn;
    this.cacheDOMElements();
    this.setupEventListeners();
    this.setupRatingStars();
  },

  cacheDOMElements() {
    this.elements.wrapper = document.getElementById(
      "visit-review-image-section",
    );
    if (!this.elements.wrapper) return;

    this.elements.form = document.getElementById("visit-review-image-form");
    this.elements.formTitlePlaceSpan = document.getElementById(
      "visit-review-place-title",
    );
    this.elements.visitDateTimeSpan = document.getElementById(
      "visit-review-datetime-display",
    );
    this.elements.visitIdInput = document.getElementById(
      "visit-review-visit-id",
    );
    this.elements.titleInput = document.getElementById("visit-review-title");
    this.elements.textInput = document.getElementById("visit-review-text");
    this.elements.ratingStarsContainer = document.getElementById(
      "visit-review-rating-stars",
    );
    this.elements.ratingInput = document.getElementById("visit-review-rating");
    this.elements.imageInput = document.getElementById("visit-review-image");
    this.elements.removeImageCheckbox = document.getElementById(
      "visit-review-remove-image",
    );
    this.elements.currentImageSection = document.getElementById(
      "current-visit-image-review-section",
    );
    this.elements.currentImageThumb = document.getElementById(
      "current-visit-image-review-thumb",
    );
    this.elements.statusMessage = document.getElementById(
      "visit-review-status",
    );
    this.elements.submitBtn = document.getElementById(
      "visit-review-image-submit-btn",
    );
    this.elements.cancelBtn = document.getElementById(
      "visit-review-cancel-btn",
    );
  },

  setupEventListeners() {
    if (!this.elements.form) return;

    this.elements.form.addEventListener("submit", (event) =>
      this.handleSubmit(event),
    );

    if (this.elements.cancelBtn && this.hideCallback) {
      this.elements.cancelBtn.addEventListener("click", () =>
        this.hideCallback(),
      );
    }

    if (this.elements.removeImageCheckbox && this.elements.imageInput) {
      this.elements.removeImageCheckbox.addEventListener("change", (event) => {
        if (event.target.checked) this.elements.imageInput.value = "";
      });
    }

    if (this.elements.imageInput && this.elements.removeImageCheckbox) {
      this.elements.imageInput.addEventListener("change", (event) => {
        if (event.target.files && event.target.files.length > 0) {
          this.elements.removeImageCheckbox.checked = false;
        }
      });
    }
  },

  populateForm(visitData, placeName = "this place") {
    if (!this.elements.form || !visitData?.id) return false;

    this.currentVisitData = visitData;
    this.currentPlaceName = placeName;
    const els = this.elements;

    els.form.reset();
    setStatusMessage(els.statusMessage, "", "info");

    if (els.formTitlePlaceSpan)
      els.formTitlePlaceSpan.textContent = `"${this.currentPlaceName}"`;
    if (els.visitIdInput) els.visitIdInput.value = visitData.id;

    if (els.visitDateTimeSpan && visitData.visit_datetime) {
      const visitDate = new Date(visitData.visit_datetime);
      els.visitDateTimeSpan.textContent = visitDate.toLocaleString(undefined, {
        year: "numeric",
        month: "long",
        day: "numeric",
        hour: "2-digit",
        minute: "2-digit",
      });
    }

    if (els.titleInput) els.titleInput.value = visitData.review_title || "";
    if (els.textInput) els.textInput.value = visitData.review_text || "";

    const currentRating = visitData.rating || "";
    if (els.ratingInput) els.ratingInput.value = currentRating;
    this.updateRatingStars(els.ratingStarsContainer, currentRating);

    if (els.imageInput) els.imageInput.value = "";
    if (els.removeImageCheckbox) els.removeImageCheckbox.checked = false;

    if (els.currentImageSection && els.currentImageThumb) {
      if (visitData.image_url) {
        els.currentImageThumb.src = visitData.image_url;
        els.currentImageSection.style.display = "block";
      } else {
        els.currentImageSection.style.display = "none";
      }
    }

    if (els.submitBtn) {
      els.submitBtn.disabled = false;
      els.submitBtn.textContent = "Save Review & Image";
    }
    return true;
  },

  async handleSubmit(event) {
    event.preventDefault();
    if (!this.elements.form || !this.currentVisitData?.id) return;

    setStatusMessage(
      this.elements.statusMessage,
      "Saving review...",
      "loading",
    );
    if (this.elements.submitBtn) this.elements.submitBtn.disabled = true;

    const visitId = this.currentVisitData.id;
    const formData = new FormData();

    formData.append("review_title", this.elements.titleInput.value.trim());
    formData.append("review_text", this.elements.textInput.value.trim());

    const ratingVal = this.elements.ratingInput.value;
    if (ratingVal) formData.append("rating", ratingVal);

    if (this.elements.imageInput?.files?.[0]) {
      formData.append("image_file", this.elements.imageInput.files[0]);
    } else if (this.elements.removeImageCheckbox?.checked) {
      formData.append("image_url_action", "remove");
    }

    try {
      const response = await apiClient.fetch(`/api/v1/visits/${visitId}`, {
        method: "PUT",
        body: formData,
      });
      const result = await response.json();

      if (response.ok) {
        setStatusMessage(
          els.statusMessage,
          "Review saved successfully!",
          "success",
        );
        if (this.onReviewSavedCallback) {
          this.onReviewSavedCallback(result);
        }
      } else {
        setStatusMessage(
          this.elements.statusMessage,
          result.detail || "Failed to save review.",
          "error",
        );
        if (this.elements.submitBtn) this.elements.submitBtn.disabled = false;
      }
    } catch (error) {
      console.error("Error saving visit review:", error);
      setStatusMessage(
        this.elements.statusMessage,
        "An error occurred. Please try again.",
        "error",
      );
      if (this.elements.submitBtn) this.elements.submitBtn.disabled = false;
    }
  },

  setupRatingStars() {
    if (!this.elements.ratingStarsContainer || !this.elements.ratingInput)
      return;
    this.setupInteractiveStars(
      this.elements.ratingStarsContainer,
      this.elements.ratingInput,
    );
  },

  setupInteractiveStars(container, hiddenInput) {
    const stars = container.querySelectorAll(".star");
    const setRating = (value) => {
      hiddenInput.value = value;
      this.updateRatingStars(container, value);
    };
    stars.forEach((star) => {
      star.addEventListener("click", (e) => {
        e.stopPropagation();
        const value = star.dataset.value;
        setRating(hiddenInput.value === value ? "" : value);
      });
      star.addEventListener("mouseover", () =>
        this.highlightStars(container, star.dataset.value),
      );
      star.addEventListener("mouseout", () =>
        this.updateRatingStars(container, hiddenInput.value),
      );
    });
    this.updateRatingStars(container, hiddenInput.value);
  },

  highlightStars(container, value) {
    const stars = container.querySelectorAll(".star");
    const val = parseInt(value, 10) || 0;
    stars.forEach((star) => {
      const starVal = parseInt(star.dataset.value, 10);
      const icon = star.querySelector("i");
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
    this.highlightStars(container, selectedValue);
  },
};

export default reviewForm;
