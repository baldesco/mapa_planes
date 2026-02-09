/**
 * reviewForm.js
 * Manages interactions and state for the Add/Edit Review & Image form for a visit.
 * Updated for SPA-lite behavior to update local state without reloads.
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
    this.elements.cancelBtn =
      this.elements.wrapper.querySelector("button.cancel-btn");
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

    this.elements.imageInput?.addEventListener("change", (event) => {
      if (event.target.files?.length > 0 && this.elements.removeImageCheckbox) {
        this.elements.removeImageCheckbox.checked = false;
      }
    });
  },

  populateForm(visitData, placeName = "this place") {
    if (!this.elements.form || !visitData?.id) return false;

    this.currentVisitData = visitData;
    this.currentPlaceName = placeName;
    const els = this.elements;

    els.form.reset();
    setStatusMessage(els.statusMessage, "", "info");

    els.formTitlePlaceSpan.textContent = `"${this.currentPlaceName}"`;
    els.visitIdInput.value = visitData.id;

    if (visitData.visit_datetime) {
      const dt = new Date(visitData.visit_datetime);
      els.visitDateTimeSpan.textContent =
        dt.toLocaleDateString() +
        " " +
        dt.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
    }

    els.titleInput.value = visitData.review_title || "";
    els.textInput.value = visitData.review_text || "";
    els.ratingInput.value = visitData.rating || "";
    this.updateRatingStars(els.ratingStarsContainer, visitData.rating || "");

    if (visitData.image_url) {
      els.currentImageThumb.src = visitData.image_url;
      els.currentImageSection.style.display = "block";
    } else {
      els.currentImageSection.style.display = "none";
    }

    els.submitBtn.disabled = false;
    return true;
  },

  async handleSubmit(event) {
    event.preventDefault();
    const visitId = this.currentVisitData.id;

    setStatusMessage(
      this.elements.statusMessage,
      "Saving review...",
      "loading",
    );
    this.elements.submitBtn.disabled = true;

    const formData = new FormData();
    if (this.elements.titleInput.value)
      formData.append("review_title", this.elements.titleInput.value);
    if (this.elements.textInput.value)
      formData.append("review_text", this.elements.textInput.value);
    if (this.elements.ratingInput.value)
      formData.append("rating", this.elements.ratingInput.value);

    if (this.elements.imageInput.files[0]) {
      formData.append("image_file", this.elements.imageInput.files[0]);
    } else if (this.elements.removeImageCheckbox?.checked) {
      formData.append("image_url_action", "remove");
    }

    try {
      const response = await apiClient.fetch(`/api/v1/visits/${visitId}`, {
        method: "PUT",
        body: formData,
      });

      if (response.ok) {
        const result = await response.json();
        setStatusMessage(
          this.elements.statusMessage,
          "Review saved!",
          "success",
        );
        if (this.onReviewSavedCallback) {
          this.onReviewSavedCallback(result);
        }
      } else {
        const error = await response.json();
        setStatusMessage(
          this.elements.statusMessage,
          error.detail || "Save failed",
          "error",
        );
        this.elements.submitBtn.disabled = false;
      }
    } catch (error) {
      setStatusMessage(this.elements.statusMessage, "Network error", "error");
      this.elements.submitBtn.disabled = false;
    }
  },

  setupRatingStars() {
    const container = this.elements.ratingStarsContainer;
    const input = this.elements.ratingInput;
    if (!container || !input) return;

    container.querySelectorAll(".star").forEach((star) => {
      star.addEventListener("click", () => {
        const val = star.dataset.value;
        input.value = input.value === val ? "" : val;
        this.updateRatingStars(container, input.value);
      });
    });
  },

  updateRatingStars(container, val) {
    const rating = parseInt(val) || 0;
    container.querySelectorAll(".star").forEach((star) => {
      const starVal = parseInt(star.dataset.value);
      const icon = star.querySelector("i");
      if (starVal <= rating) {
        icon.classList.replace("far", "fas");
        star.classList.add("selected");
      } else {
        icon.classList.replace("fas", "far");
        star.classList.remove("selected");
      }
    });
  },
};

export default reviewForm;
