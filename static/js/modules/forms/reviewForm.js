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
    
    this.elements.photosManagementSection = document.getElementById(
      "visit-photos-management-section",
    );
    this.elements.photosList = document.getElementById("visit-photos-list");
    
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

    this.renderPhotosList(visitData.photos || []);

    if (els.submitBtn) {
      els.submitBtn.disabled = false;
      els.submitBtn.textContent = "Save Review & Photos";
    }
    return true;
  },

  renderPhotosList(photos) {
    const els = this.elements;
    if (!els.photosList) return;

    els.photosList.innerHTML = "";
    if (photos.length > 0) {
      els.photosManagementSection.style.display = "block";
      photos.forEach((photo) => {
        const photoDiv = document.createElement("div");
        photoDiv.className = `visit-photo-item ${photo.is_main ? "is-main" : ""}`;
        photoDiv.innerHTML = `
          <div class="photo-thumb-wrapper">
            <img src="${photo.image_url}" alt="Visit photo">
            ${photo.is_main ? '<span class="main-badge">Main</span>' : ""}
          </div>
          <div class="photo-item-actions">
            ${!photo.is_main ? `<button type="button" class="btn-set-main" data-id="${photo.id}">Make Main</button>` : ""}
            <button type="button" class="btn-delete-photo" data-id="${photo.id}"><i class="fas fa-trash"></i></button>
          </div>
        `;
        
        // Add event listeners
        const mainBtn = photoDiv.querySelector(".btn-set-main");
        if (mainBtn) {
          mainBtn.addEventListener("click", () => this.handleSetMainPhoto(photo.id));
        }
        
        photoDiv.querySelector(".btn-delete-photo").addEventListener("click", () => this.handleDeletePhoto(photo.id));
        
        els.photosList.appendChild(photoDiv);
      });
    } else {
      els.photosManagementSection.style.display = "none";
    }
  },

  async handleSetMainPhoto(photoId) {
    const visitId = this.currentVisitData.id;
    try {
      const response = await apiClient.patch(`/api/v1/visits/${visitId}/photos/${photoId}/main`);
      if (response.ok) {
        // Refresh the form data
        const updatedVisitRes = await apiClient.get(`/api/v1/visits/${visitId}`);
        if (updatedVisitRes.ok) {
           const updatedVisit = await updatedVisitRes.json();
           this.populateForm(updatedVisit, this.currentPlaceName);
        }
      } else {
        const error = await response.json();
        alert(`Error setting main photo: ${error.detail}`);
      }
    } catch (e) {
      console.error("Error setting main photo:", e);
    }
  },

  async handleDeletePhoto(photoId) {
    if (!confirm("Are you sure you want to delete this photo?")) return;
    
    const visitId = this.currentVisitData.id;
    try {
      const response = await apiClient.delete(`/api/v1/visits/${visitId}/photos/${photoId}`);
      if (response.ok) {
        // Refresh the form data
        const updatedVisitRes = await apiClient.get(`/api/v1/visits/${visitId}`);
        if (updatedVisitRes.ok) {
           const updatedVisit = await updatedVisitRes.json();
           this.populateForm(updatedVisit, this.currentPlaceName);
        }
      } else {
        const error = await response.json();
        alert(`Error deleting photo: ${error.detail}`);
      }
    } catch (e) {
      console.error("Error deleting photo:", e);
    }
  },

  async handleSubmit(event) {
    event.preventDefault();
    if (!this.elements.form || !this.currentVisitData?.id) return;

    setStatusMessage(
      this.elements.statusMessage,
      "Saving review and photos...",
      "loading",
    );
    if (this.elements.submitBtn) this.elements.submitBtn.disabled = true;

    const visitId = this.currentVisitData.id;
    
    // 1. Update basic visit info (review, rating)
    const formData = new FormData();
    formData.append("review_title", this.elements.titleInput.value.trim());
    formData.append("review_text", this.elements.textInput.value.trim());
    const ratingVal = this.elements.ratingInput.value;
    if (ratingVal) formData.append("rating", ratingVal);

    try {
      const response = await apiClient.fetch(`/api/v1/visits/${visitId}`, {
        method: "PUT",
        body: formData,
      });

      if (!response.ok) {
        const result = await response.json();
        throw new Error(result.detail || "Failed to save review.");
      }

      // 2. Upload new photos if any
      const photofiles = this.elements.imageInput.files;
      if (photofiles && photofiles.length > 0) {
        for (let i = 0; i < photofiles.length; i++) {
          setStatusMessage(
            this.elements.statusMessage,
            `Uploading photo ${i + 1} of ${photofiles.length}...`,
            "loading",
          );
          
          const photoFormData = new FormData();
          photoFormData.append("image_file", photofiles[i]);
          
          const photoRes = await apiClient.fetch(`/api/v1/visits/${visitId}/photos`, {
            method: "POST",
            body: photoFormData
          });
          
          if (!photoRes.ok) {
            console.error(`Failed to upload photo ${i+1}`);
          }
        }
      }

      // 3. Success! Get full updated visit data
      const finalRes = await apiClient.get(`/api/v1/visits/${visitId}`);
      const finalResult = await finalRes.json();

      setStatusMessage(
        this.elements.statusMessage,
        "Review and photos saved successfully!",
        "success",
      );
      
      if (this.onReviewSavedCallback) {
        this.onReviewSavedCallback(finalResult);
      }
    } catch (error) {
      console.error("Error saving visit review:", error);
      setStatusMessage(
        this.elements.statusMessage,
        error.message || "An error occurred. Please try again.",
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
