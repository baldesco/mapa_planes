/**
 * reviewForm.js
 * Manages interactions and state for the Add/Edit Review & Image form FOR A VISIT.
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
  onReviewSavedCallback: null, // This is uiOrchestrator.handleVisitSaved
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
      "visit-review-image-section"
    );
    if (!this.elements.wrapper) {
      console.error(
        "Visit Review Form: Wrapper element #visit-review-image-section not found."
      );
      return;
    }
    this.elements.form = document.getElementById("visit-review-image-form");
    this.elements.formTitlePlaceSpan = document.getElementById(
      "visit-review-place-title"
    );
    this.elements.visitDateTimeSpan = document.getElementById(
      "visit-review-datetime-display"
    );
    this.elements.visitIdInput = document.getElementById(
      "visit-review-visit-id"
    );
    this.elements.titleInput = document.getElementById("visit-review-title");
    this.elements.textInput = document.getElementById("visit-review-text");
    this.elements.ratingStarsContainer = document.getElementById(
      "visit-review-rating-stars"
    );
    this.elements.ratingInput = document.getElementById("visit-review-rating");
    this.elements.imageInput = document.getElementById("visit-review-image");
    this.elements.removeImageCheckbox = document.getElementById(
      "visit-review-remove-image"
    );
    this.elements.currentImageSection = document.getElementById(
      "current-visit-image-review-section"
    );
    this.elements.currentImageThumb = document.getElementById(
      "current-visit-image-review-thumb"
    );
    this.elements.statusMessage = document.getElementById(
      "visit-review-status"
    );
    this.elements.submitBtn = document.getElementById(
      "visit-review-image-submit-btn"
    );
    this.elements.cancelBtn = document.getElementById(
      "visit-review-cancel-btn"
    );
  },

  setupEventListeners() {
    if (!this.elements.form) return;
    this.elements.form.addEventListener("submit", (event) =>
      this.handleSubmit(event)
    );
    if (this.elements.cancelBtn && this.hideCallback) {
      this.elements.cancelBtn.addEventListener("click", () =>
        this.hideCallback()
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
    if (!this.elements.form || !visitData || !visitData.id) {
      console.error(
        "Visit Review Form: Cannot populate - missing form, visitData, or visit ID."
      );
      return false;
    }
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
      const formattedDate = visitDate.toLocaleDateString(undefined, {
        year: "numeric",
        month: "long",
        day: "numeric",
      });
      const formattedTime = visitDate.toLocaleTimeString(undefined, {
        hour: "2-digit",
        minute: "2-digit",
      });
      els.visitDateTimeSpan.textContent = `${formattedDate} at ${formattedTime}`;
    }

    if (els.titleInput) els.titleInput.value = visitData.review_title || "";
    if (els.textInput) els.textInput.value = visitData.review_text || "";

    const currentRating =
      visitData.rating !== null && visitData.rating !== undefined
        ? String(visitData.rating)
        : "";
    if (els.ratingInput) els.ratingInput.value = currentRating;
    this.updateRatingStars(els.ratingStarsContainer, currentRating);

    if (els.imageInput) els.imageInput.value = "";
    if (els.removeImageCheckbox) els.removeImageCheckbox.checked = false;

    if (els.currentImageSection && els.currentImageThumb) {
      if (visitData.image_url && visitData.image_url.startsWith("http")) {
        els.currentImageThumb.src = visitData.image_url;
        els.currentImageThumb.alt = `Image for visit to ${this.currentPlaceName}`;
        els.currentImageSection.style.display = "block";
      } else {
        els.currentImageThumb.src = "";
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
    if (
      !this.elements.form ||
      !this.currentVisitData ||
      !this.currentVisitData.id
    ) {
      setStatusMessage(
        this.elements.statusMessage,
        "Error: Missing visit information.",
        "error"
      );
      return;
    }
    setStatusMessage(
      this.elements.statusMessage,
      "Saving review...",
      "loading"
    );
    if (this.elements.submitBtn) this.elements.submitBtn.disabled = true;

    const visitId = this.currentVisitData.id;
    const formData = new FormData();

    if (this.elements.titleInput.value.trim())
      formData.append("review_title", this.elements.titleInput.value.trim());
    if (this.elements.textInput.value.trim())
      formData.append("review_text", this.elements.textInput.value.trim());
    if (this.elements.ratingInput.value)
      formData.append("rating", this.elements.ratingInput.value);

    if (
      this.elements.imageInput &&
      this.elements.imageInput.files &&
      this.elements.imageInput.files[0]
    ) {
      formData.append("image_file", this.elements.imageInput.files[0]);
    } else if (
      this.elements.removeImageCheckbox &&
      this.elements.removeImageCheckbox.checked
    ) {
      formData.append("image_url_action", "remove");
    }

    try {
      const apiUrl = `/api/v1/visits/${visitId}`;
      const response = await apiClient.fetch(apiUrl, {
        method: "PUT",
        body: formData,
      });
      const result = await response.json();

      if (response.ok) {
        setStatusMessage(
          this.elements.statusMessage,
          "Review saved successfully!",
          "success"
        );
        if (this.onReviewSavedCallback) {
          this.onReviewSavedCallback(result);
        }
        // No automatic hide timeout here, page reload from onReviewSavedCallback will handle it
      } else {
        setStatusMessage(
          this.elements.statusMessage,
          result.detail || "Failed to save review.",
          "error"
        );
        if (this.elements.submitBtn) this.elements.submitBtn.disabled = false;
      }
    } catch (error) {
      console.error("Error saving visit review:", error);
      setStatusMessage(
        this.elements.statusMessage,
        "An error occurred. Please try again.",
        "error"
      );
      if (this.elements.submitBtn) this.elements.submitBtn.disabled = false;
    }
  },

  setupRatingStars() {
    if (!this.elements.ratingStarsContainer || !this.elements.ratingInput)
      return;
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
        if (hiddenInput.value === value) setRating("");
        else setRating(value);
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
};
export default reviewForm;
