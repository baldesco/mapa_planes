/**
 * modals.js
 * Handles showing/hiding modal dialogs like the "See Visit Review" modal
 * and the full-screen image overlay.
 */
// setStatusMessage is not used directly here, but good to keep if modals evolve
// import { setStatusMessage } from "./statusMessages.js";

const modals = {
  elements: {
    // See Visit Review Modal Elements (IDs updated in HTML)
    seeVisitReviewSection: null,
    seeVisitReviewPlaceTitle: null,
    seeVisitReviewDateTime: null, // To display visit date/time
    seeVisitReviewRatingDisplay: null,
    seeVisitReviewDisplayTitle: null,
    seeVisitReviewDisplayText: null,
    seeVisitReviewDisplayImage: null,
    seeVisitReviewEditBtn: null,
    seeVisitReviewCloseBtn: null,
    imageOverlayInstance: null,
  },
  currentVisitDataForReviewModal: null, // Store visit data
  currentPlaceNameForReviewModal: null, // Store place name
  editVisitReviewCallback: null, // Function from orchestrator to show the edit review form

  init(editReviewFn) {
    console.debug("Modals Component: Initializing...");
    this.editVisitReviewCallback = editReviewFn; // This will be uiOrchestrator.showVisitReviewForm
    this.cacheDOMElements();
    this.setupEventListeners();
  },

  cacheDOMElements() {
    // IDs updated to match HTML
    this.elements.seeVisitReviewSection = document.getElementById(
      "see-visit-review-section"
    );
    if (!this.elements.seeVisitReviewSection) return;

    this.elements.seeVisitReviewPlaceTitle = document.getElementById(
      "see-visit-review-place-title"
    );
    this.elements.seeVisitReviewDateTime = document.getElementById(
      "see-visit-review-datetime-display"
    );
    this.elements.seeVisitReviewRatingDisplay = document.getElementById(
      "see-visit-review-rating-display"
    );
    this.elements.seeVisitReviewDisplayTitle = document.getElementById(
      "see-visit-review-display-title"
    );
    this.elements.seeVisitReviewDisplayText = document.getElementById(
      "see-visit-review-display-text"
    );
    this.elements.seeVisitReviewDisplayImage = document.getElementById(
      "see-visit-review-display-image"
    );
    this.elements.seeVisitReviewEditBtn = document.getElementById(
      "see-visit-review-edit-btn"
    );
    this.elements.seeVisitReviewCloseBtn = document.getElementById(
      "see-visit-review-close-btn"
    );
  },

  setupEventListeners() {
    if (this.elements.seeVisitReviewCloseBtn) {
      this.elements.seeVisitReviewCloseBtn.addEventListener("click", () =>
        this.hideSeeReviewModal()
      );
    }

    if (this.elements.seeVisitReviewEditBtn && this.editVisitReviewCallback) {
      this.elements.seeVisitReviewEditBtn.addEventListener("click", () => {
        if (this.currentVisitDataForReviewModal) {
          // Call orchestrator's function to show the actual review form for this visit
          this.editVisitReviewCallback(
            this.currentVisitDataForReviewModal,
            this.currentPlaceNameForReviewModal
          );
        } else {
          console.error("Cannot edit visit review, data missing.");
          alert("Error: Could not retrieve data to edit review.");
        }
        this.hideSeeReviewModal(); // Hide this modal after clicking edit
      });
    }

    if (this.elements.seeVisitReviewDisplayImage) {
      this.elements.seeVisitReviewDisplayImage.addEventListener(
        "click",
        (event) => this.showImageOverlay(event)
      );
    }
  },

  displayStaticRatingStars(container, rating) {
    if (!container) return;
    const numRating = parseInt(rating, 10);
    if (numRating >= 1 && numRating <= 5) {
      let html = "";
      for (let i = 1; i <= 5; i++) {
        html += `<i class="${i <= numRating ? "fas" : "far"} fa-star"></i> `;
      }
      container.innerHTML = html.trim();
      container.style.display = "inline-block";
    } else {
      container.innerHTML = "(No rating for this visit)"; // Updated text
      container.style.display = "inline-block";
    }
  },

  showSeeReviewModal(visitDataInput, placeName = "this place") {
    // Now takes visitData and placeName
    let visitData;
    if (typeof visitDataInput === "string") {
      try {
        visitData = JSON.parse(visitDataInput);
      } catch (e) {
        console.error("Modals: Error parsing visitData JSON:", e);
        alert("Error reading visit data.");
        return;
      }
    } else if (typeof visitDataInput === "object" && visitDataInput !== null) {
      visitData = visitDataInput;
    } else {
      console.error("Modals: Invalid input type for showSeeReviewModal.");
      alert("Internal Error: Invalid data for review modal.");
      return;
    }

    this.currentVisitDataForReviewModal = visitData;
    this.currentPlaceNameForReviewModal = placeName;
    const els = this.elements;

    if (!els.seeVisitReviewSection) {
      console.error("Modals: See Visit Review section element missing.");
      return;
    }

    try {
      if (els.seeVisitReviewPlaceTitle)
        els.seeVisitReviewPlaceTitle.textContent = `"${this.currentPlaceNameForReviewModal}"`;

      if (els.seeVisitReviewDateTime && visitData.visit_datetime) {
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
        els.seeVisitReviewDateTime.textContent = `${formattedDate} at ${formattedTime}`;
      } else if (els.seeVisitReviewDateTime) {
        els.seeVisitReviewDateTime.textContent = "(Date/Time not available)";
      }

      this.displayStaticRatingStars(
        els.seeVisitReviewRatingDisplay,
        visitData.rating
      );
      if (els.seeVisitReviewDisplayTitle)
        els.seeVisitReviewDisplayTitle.textContent =
          visitData.review_title || "";
      if (els.seeVisitReviewDisplayText)
        els.seeVisitReviewDisplayText.textContent =
          visitData.review_text ||
          (visitData.review_title || visitData.rating
            ? ""
            : "(No review text for this visit)");
      if (els.seeVisitReviewDisplayTitle)
        els.seeVisitReviewDisplayTitle.style.display = visitData.review_title
          ? "block"
          : "none";

      if (els.seeVisitReviewDisplayImage) {
        if (visitData.image_url && visitData.image_url.startsWith("http")) {
          els.seeVisitReviewDisplayImage.src = visitData.image_url;
          els.seeVisitReviewDisplayImage.alt = `Image for visit to ${this.currentPlaceNameForReviewModal}`;
          els.seeVisitReviewDisplayImage.style.display = "block";
        } else {
          els.seeVisitReviewDisplayImage.style.display = "none";
          els.seeVisitReviewDisplayImage.src = "";
        }
      }
      els.seeVisitReviewSection.style.display = "block";
      els.seeVisitReviewSection.scrollIntoView({
        behavior: "smooth",
        block: "center",
      });
    } catch (e) {
      console.error("Modals: Error populating see visit review modal:", e);
      alert("Error preparing review display.");
      this.hideSeeReviewModal();
    }
  },

  hideSeeReviewModal() {
    if (this.elements.seeVisitReviewSection) {
      this.elements.seeVisitReviewSection.style.display = "none";
    }
    this.currentVisitDataForReviewModal = null;
    this.currentPlaceNameForReviewModal = null;
  },

  showImageOverlay(event) {
    /* ... same as before ... */
  },
  hideImageOverlay() {
    /* ... same as before ... */
  },
};

export default modals;
