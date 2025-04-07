/**
 * modals.js
 * Handles showing/hiding modal dialogs like the "See Review" modal
 * and the full-screen image overlay.
 */

const modals = {
  elements: {
    // See Review Modal Elements
    seeReviewSection: null,
    seeReviewPlaceTitle: null,
    seeReviewRatingDisplay: null,
    seeReviewDisplayTitle: null,
    seeReviewDisplayText: null,
    seeReviewDisplayImage: null,
    seeReviewEditBtn: null,
    seeReviewCloseBtn: null,
    // Image Overlay (dynamically created, but we might need a reference)
    imageOverlayInstance: null,
  },
  currentPlaceDataForReviewModal: null, // Store data specifically for the review modal
  showReviewFormCallback: null, // Function provided by orchestrator to show the edit review form

  init(showReviewFn) {
    console.debug("Modals Component: Initializing...");
    this.showReviewFormCallback = showReviewFn;
    this.cacheDOMElements();
    this.setupEventListeners();
  },

  cacheDOMElements() {
    this.elements.seeReviewSection =
      document.getElementById("see-review-section");
    if (!this.elements.seeReviewSection) return; // Stop if section missing

    this.elements.seeReviewPlaceTitle = document.getElementById(
      "see-review-place-title"
    );
    this.elements.seeReviewRatingDisplay = document.getElementById(
      "see-review-rating-display"
    );
    this.elements.seeReviewDisplayTitle = document.getElementById(
      "see-review-display-title"
    );
    this.elements.seeReviewDisplayText = document.getElementById(
      "see-review-display-text"
    );
    this.elements.seeReviewDisplayImage = document.getElementById(
      "see-review-display-image"
    );
    this.elements.seeReviewEditBtn = document.getElementById(
      "see-review-edit-btn"
    );
    this.elements.seeReviewCloseBtn =
      this.elements.seeReviewSection.querySelector("button.cancel-btn");
  },

  setupEventListeners() {
    if (this.elements.seeReviewCloseBtn) {
      this.elements.seeReviewCloseBtn.addEventListener("click", () =>
        this.hideSeeReviewModal()
      );
    }

    if (this.elements.seeReviewEditBtn && this.showReviewFormCallback) {
      this.elements.seeReviewEditBtn.addEventListener("click", () => {
        if (this.currentPlaceDataForReviewModal) {
          // Call the orchestrator's function to show the actual review form
          this.showReviewFormCallback(this.currentPlaceDataForReviewModal);
        } else {
          console.error("Cannot edit review, data missing.");
          alert("Error: Could not retrieve data to edit review.");
        }
        // Hide this modal after clicking edit
        this.hideSeeReviewModal();
      });
    }

    // Image overlay closing is handled dynamically when created/shown
    // Add listener for clicking the review image to show overlay
    if (this.elements.seeReviewDisplayImage) {
      this.elements.seeReviewDisplayImage.addEventListener("click", (event) =>
        this.showImageOverlay(event)
      );
    }
  },

  /** Displays static rating stars in a container */
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
      container.innerHTML = "(No rating)";
      container.style.display = "inline-block";
    }
  },

  /** Shows the "See Review" modal with place data */
  showSeeReviewModal(placeDataInput) {
    let placeData;
    // Safely parse input
    if (typeof placeDataInput === "string") {
      try {
        placeData = JSON.parse(placeDataInput);
      } catch (e) {
        console.error(
          "Modals: Error parsing placeData JSON for see review:",
          e
        );
        alert("Error reading place data for review display.");
        return;
      }
    } else if (typeof placeDataInput === "object" && placeDataInput !== null) {
      placeData = placeDataInput;
    } else {
      console.error("Modals: Invalid input type for showSeeReviewModal.");
      alert("Internal Error: Invalid data for review modal.");
      return;
    }

    this.currentPlaceDataForReviewModal = placeData; // Store data

    const els = this.elements;
    if (!els.seeReviewSection) {
      console.error("Modals: See Review section element missing.");
      return;
    }

    try {
      // Populate modal content
      els.seeReviewPlaceTitle.textContent = `"${
        placeData.name || "Unknown Place"
      }"`;
      this.displayStaticRatingStars(
        els.seeReviewRatingDisplay,
        placeData.rating
      );
      els.seeReviewDisplayTitle.textContent = placeData.review_title || "";
      els.seeReviewDisplayText.textContent =
        placeData.review ||
        (placeData.review_title || placeData.rating
          ? ""
          : "(No review text entered)");
      els.seeReviewDisplayTitle.style.display = placeData.review_title
        ? "block"
        : "none";

      if (els.seeReviewDisplayImage) {
        if (placeData.image_url && placeData.image_url.startsWith("http")) {
          els.seeReviewDisplayImage.src = placeData.image_url;
          els.seeReviewDisplayImage.alt = `Image for ${
            placeData.name || "place"
          }`;
          els.seeReviewDisplayImage.style.display = "block";
        } else {
          els.seeReviewDisplayImage.style.display = "none";
          els.seeReviewDisplayImage.src = "";
        }
      }

      // Show modal (assuming other sections are hidden by orchestrator)
      els.seeReviewSection.style.display = "block";
      els.seeReviewSection.scrollIntoView({
        behavior: "smooth",
        block: "start",
      });
    } catch (e) {
      console.error("Modals: Error populating see review modal:", e);
      alert("Error preparing review display.");
      this.hideSeeReviewModal(); // Hide on error
    }
  },

  /** Hides the "See Review" modal */
  hideSeeReviewModal() {
    if (this.elements.seeReviewSection) {
      this.elements.seeReviewSection.style.display = "none";
    }
    this.currentPlaceDataForReviewModal = null; // Clear stored data
  },

  /** Shows the full-screen image overlay */
  showImageOverlay(event) {
    const clickedImage = event.target;
    // Check if the clicked element is an IMG tag with a valid src
    if (
      !clickedImage ||
      clickedImage.tagName !== "IMG" ||
      !clickedImage.src ||
      !clickedImage.src.startsWith("http")
    ) {
      console.debug("showImageOverlay: Click target not a valid image.");
      return;
    }

    // Prevent default if inside a link etc.
    event.preventDefault();
    event.stopPropagation();

    // Find or create the overlay
    this.elements.imageOverlayInstance =
      document.querySelector(".image-overlay");
    if (!this.elements.imageOverlayInstance) {
      this.elements.imageOverlayInstance = document.createElement("div");
      this.elements.imageOverlayInstance.className = "image-overlay";
      const img = document.createElement("img");
      img.alt = "Enlarged image"; // Alt text can be improved if needed
      // Prevent closing overlay by clicking the image itself
      img.onclick = (e) => e.stopPropagation();
      this.elements.imageOverlayInstance.appendChild(img);
      // Close overlay by clicking the background
      this.elements.imageOverlayInstance.onclick =
        this.hideImageOverlay.bind(this);
      document.body.appendChild(this.elements.imageOverlayInstance);
    }

    // Set the image source and make visible
    this.elements.imageOverlayInstance.querySelector("img").src =
      clickedImage.src;
    this.elements.imageOverlayInstance.querySelector("img").alt =
      clickedImage.alt || "Enlarged image"; // Use original alt text

    // Use setTimeout to allow the element to be added to DOM before adding 'visible' class for transition
    setTimeout(() => {
      if (this.elements.imageOverlayInstance) {
        this.elements.imageOverlayInstance.classList.add("visible");
      }
    }, 10);
  },

  /** Hides the full-screen image overlay */
  hideImageOverlay() {
    if (
      this.elements.imageOverlayInstance &&
      this.elements.imageOverlayInstance.classList.contains("visible")
    ) {
      this.elements.imageOverlayInstance.classList.remove("visible");
      // Remove the overlay from DOM after transition ends
      this.elements.imageOverlayInstance.addEventListener(
        "transitionend",
        () => {
          if (
            this.elements.imageOverlayInstance &&
            document.body.contains(this.elements.imageOverlayInstance)
          ) {
            document.body.removeChild(this.elements.imageOverlayInstance);
          }
          this.elements.imageOverlayInstance = null; // Clear reference
        },
        { once: true }
      );
    } else {
      // If called unexpectedly, ensure any lingering overlay is removed
      const existingOverlay = document.querySelector(".image-overlay");
      if (existingOverlay && document.body.contains(existingOverlay)) {
        document.body.removeChild(existingOverlay);
      }
      this.elements.imageOverlayInstance = null;
    }
  },
};

export default modals;
