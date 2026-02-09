/**
 * modals.js
 * Handles showing/hiding modal dialogs and the image overlay.
 * Updated to support SPA-lite transitions and consistent state handling.
 */

const modals = {
  elements: {
    seeVisitReviewSection: null,
    seeVisitReviewPlaceTitle: null,
    seeVisitReviewDateTime: null,
    seeVisitReviewRatingDisplay: null,
    seeVisitReviewDisplayTitle: null,
    seeVisitReviewDisplayText: null,
    seeVisitReviewDisplayImage: null,
    seeVisitReviewEditBtn: null,
    imageOverlayInstance: null,
  },
  currentVisitData: null,
  currentPlaceName: null,
  editVisitReviewCallback: null,

  init(editReviewFn) {
    this.editVisitReviewCallback = editReviewFn;
    this.cacheDOMElements();
    this.setupEventListeners();
  },

  cacheDOMElements() {
    this.elements.seeVisitReviewSection = document.getElementById(
      "see-visit-review-section",
    );
    if (!this.elements.seeVisitReviewSection) return;

    this.elements.seeVisitReviewPlaceTitle = document.getElementById(
      "see-visit-review-place-title",
    );
    this.elements.seeVisitReviewDateTime = document.getElementById(
      "see-visit-review-datetime-display",
    );
    this.elements.seeVisitReviewRatingDisplay = document.getElementById(
      "see-visit-review-rating-display",
    );
    this.elements.seeVisitReviewDisplayTitle = document.getElementById(
      "see-visit-review-display-title",
    );
    this.elements.seeVisitReviewDisplayText = document.getElementById(
      "see-visit-review-display-text",
    );
    this.elements.seeVisitReviewDisplayImage = document.getElementById(
      "see-visit-review-display-image",
    );
    this.elements.seeVisitReviewEditBtn = document.getElementById(
      "see-visit-review-edit-btn",
    );
  },

  setupEventListeners() {
    if (!this.elements.seeVisitReviewSection) return;

    // Close button within the modal
    this.elements.seeVisitReviewSection
      .querySelector(".cancel-btn")
      ?.addEventListener("click", () => {
        this.hideSeeReviewModal();
      });

    // Edit button triggers the review form via the orchestrator callback
    this.elements.seeVisitReviewEditBtn?.addEventListener("click", () => {
      if (this.currentVisitData && this.editVisitReviewCallback) {
        const data = this.currentVisitData;
        const name = this.currentPlaceName;
        this.hideSeeReviewModal();
        this.editVisitReviewCallback(data, name);
      }
    });

    this.elements.seeVisitReviewDisplayImage?.addEventListener("click", (e) =>
      this.showImageOverlay(e),
    );
  },

  /**
   * Populates and shows the review modal.
   */
  showSeeReviewModal(visitData, placeName = "this place") {
    const data =
      typeof visitData === "string" ? JSON.parse(visitData) : visitData;
    if (!data?.id) return;

    this.currentVisitData = data;
    this.currentPlaceName = placeName;
    const els = this.elements;

    els.seeVisitReviewPlaceTitle.textContent = placeName;

    if (data.visit_datetime) {
      const dt = new Date(data.visit_datetime);
      els.seeVisitReviewDateTime.textContent = dt.toLocaleDateString();
    }

    this.renderRatingStars(els.seeVisitReviewRatingDisplay, data.rating);

    els.seeVisitReviewDisplayTitle.textContent = data.review_title || "";
    els.seeVisitReviewDisplayTitle.style.display = data.review_title
      ? "block"
      : "none";

    els.seeVisitReviewDisplayText.textContent =
      data.review_text || (data.rating ? "" : "No comments provided.");

    if (data.image_url) {
      els.seeVisitReviewDisplayImage.src = data.image_url;
      els.seeVisitReviewDisplayImage.style.display = "block";
    } else {
      els.seeVisitReviewDisplayImage.style.display = "none";
    }

    els.seeVisitReviewSection.style.display = "block";
  },

  hideSeeReviewModal() {
    if (this.elements.seeVisitReviewSection) {
      this.elements.seeVisitReviewSection.style.display = "none";
    }
    this.currentVisitData = null;
  },

  renderRatingStars(container, rating) {
    if (!container) return;
    const numRating = parseInt(rating) || 0;
    let html = "";
    for (let i = 1; i <= 5; i++) {
      html += `<i class="${i <= numRating ? "fas" : "far"} fa-star"></i>`;
    }
    container.innerHTML = html;
  },

  showImageOverlay(event) {
    const src = event.target.src;
    if (!src) return;

    const overlay = document.createElement("div");
    overlay.className = "image-overlay visible";

    const img = document.createElement("img");
    img.src = src;

    overlay.appendChild(img);
    overlay.onclick = () => overlay.remove();

    document.body.appendChild(overlay);
    this.elements.imageOverlayInstance = overlay;
  },

  hideImageOverlay() {
    if (this.elements.imageOverlayInstance) {
      this.elements.imageOverlayInstance.remove();
      this.elements.imageOverlayInstance = null;
    }
  },
};

export default modals;
