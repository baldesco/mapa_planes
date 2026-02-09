/**
 * modals.js
 * Handles showing/hiding modal dialogs like the "See Visit Review" modal
 * and the full-screen image overlay.
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
    seeVisitReviewCloseBtn: null,
    imageOverlayInstance: null,
  },
  currentVisitDataForReviewModal: null,
  currentPlaceNameForReviewModal: null,
  editVisitReviewCallback: null,

  /**
   * @param {Function} editReviewFn - Callback to show the edit review form.
   */
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
    this.elements.seeVisitReviewCloseBtn = document.getElementById(
      "see-visit-review-close-btn",
    );
  },

  setupEventListeners() {
    if (this.elements.seeVisitReviewCloseBtn) {
      this.elements.seeVisitReviewCloseBtn.addEventListener("click", () =>
        this.hideSeeReviewModal(),
      );
    }

    if (this.elements.seeVisitReviewEditBtn) {
      this.elements.seeVisitReviewEditBtn.addEventListener("click", () => {
        if (
          this.currentVisitDataForReviewModal &&
          this.editVisitReviewCallback
        ) {
          const data = this.currentVisitDataForReviewModal;
          const name = this.currentPlaceNameForReviewModal;
          this.hideSeeReviewModal();
          this.editVisitReviewCallback(data, name);
        }
      });
    }

    if (this.elements.seeVisitReviewDisplayImage) {
      this.elements.seeVisitReviewDisplayImage.addEventListener("click", (e) =>
        this.showImageOverlay(e),
      );
    }
  },

  /**
   * Renders star icons into a container.
   */
  displayStaticRatingStars(container, rating) {
    if (!container) return;
    const numRating = parseInt(rating, 10);
    if (numRating >= 1 && numRating <= 5) {
      let html = "";
      for (let i = 1; i <= 5; i++) {
        html += `<i class="${i <= numRating ? "fas" : "far"} fa-star"></i> `;
      }
      container.innerHTML = html.trim();
    } else {
      container.innerHTML = "(No rating)";
    }
  },

  /**
   * Populates and shows the review modal.
   */
  showSeeReviewModal(visitDataInput, placeName = "this place") {
    let visitData =
      typeof visitDataInput === "string"
        ? JSON.parse(visitDataInput)
        : visitDataInput;

    if (!visitData || !visitData.id) return;

    this.currentVisitDataForReviewModal = visitData;
    this.currentPlaceNameForReviewModal = placeName;
    const els = this.elements;

    els.seeVisitReviewPlaceTitle.textContent = `"${placeName}"`;

    if (visitData.visit_datetime) {
      const date = new Date(visitData.visit_datetime);
      els.seeVisitReviewDateTime.textContent = date.toLocaleString(undefined, {
        year: "numeric",
        month: "long",
        day: "numeric",
        hour: "2-digit",
        minute: "2-digit",
      });
    }

    this.displayStaticRatingStars(
      els.seeVisitReviewRatingDisplay,
      visitData.rating,
    );

    els.seeVisitReviewDisplayTitle.textContent = visitData.review_title || "";
    els.seeVisitReviewDisplayTitle.style.display = visitData.review_title
      ? "block"
      : "none";

    els.seeVisitReviewDisplayText.textContent =
      visitData.review_text || (visitData.rating ? "" : "(No review text)");

    if (visitData.image_url) {
      els.seeVisitReviewDisplayImage.src = visitData.image_url;
      els.seeVisitReviewDisplayImage.style.display = "block";
    } else {
      els.seeVisitReviewDisplayImage.style.display = "none";
    }

    els.seeVisitReviewSection.style.display = "block";
    els.seeVisitReviewSection.scrollIntoView({
      behavior: "smooth",
      block: "center",
    });
  },

  hideSeeReviewModal() {
    if (this.elements.seeVisitReviewSection) {
      this.elements.seeVisitReviewSection.style.display = "none";
    }
    this.currentVisitDataForReviewModal = null;
  },

  /**
   * Creates and shows a full-screen image overlay.
   */
  showImageOverlay(event) {
    const src = event.target.src;
    if (!src) return;

    this.elements.imageOverlayInstance = document.createElement("div");
    this.elements.imageOverlayInstance.className = "image-overlay";

    const img = document.createElement("img");
    img.src = src;

    this.elements.imageOverlayInstance.appendChild(img);
    this.elements.imageOverlayInstance.onclick = () => this.hideImageOverlay();

    document.body.appendChild(this.elements.imageOverlayInstance);

    // Trigger transition
    setTimeout(
      () => this.elements.imageOverlayInstance.classList.add("visible"),
      10,
    );
  },

  hideImageOverlay() {
    const overlay = this.elements.imageOverlayInstance;
    if (!overlay) return;

    overlay.classList.remove("visible");
    overlay.addEventListener("transitionend", () => overlay.remove(), {
      once: true,
    });
    this.elements.imageOverlayInstance = null;
  },
};

export default modals;
