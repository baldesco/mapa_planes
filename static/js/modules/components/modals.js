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
    seeVisitReviewPhotosContainer: null,
    seeVisitReviewEditBtn: null,
    seeVisitReviewCloseBtn: null,
    seeVisitReviewPrevBtn: null,
    seeVisitReviewNextBtn: null,
    seeVisitReviewDotsContainer: null,
    carouselContainer: null,
    imageOverlayInstance: null,
    actionPromptSection: null,
    actionPromptTitle: null,
    actionPromptMessage: null,
    actionPromptConfirmBtn: null,
    actionPromptCancelBtn: null,
  },
  currentVisitDataForReviewModal: null,
  currentPlaceNameForReviewModal: null,
  editVisitReviewCallback: null,
  currentSlideIndex: 0,
  totalSlides: 0,

  /**
   * @param {Function} editReviewFn - Callback to show the edit review form.
   */
  init(editReviewFn) {
    this.editVisitReviewCallback = editReviewFn;
    this.cacheDOMElements();
    this.setupEventListeners();
  },

  cacheDOMElements() {
    this.elements.seeVisitReviewSection = document.getElementById("see-visit-review-section");
    if (!this.elements.seeVisitReviewSection) return;

    this.elements.seeVisitReviewPlaceTitle = document.getElementById("see-visit-review-place-title");
    this.elements.seeVisitReviewDateTime = document.getElementById("see-visit-review-datetime-display");
    this.elements.seeVisitReviewRatingDisplay = document.getElementById("see-visit-review-rating-display");
    this.elements.seeVisitReviewDisplayTitle = document.getElementById("see-visit-review-display-title");
    this.elements.seeVisitReviewDisplayText = document.getElementById("see-visit-review-display-text");
    this.elements.seeVisitReviewPhotosContainer = document.getElementById("see-visit-review-photos-container");
    this.elements.seeVisitReviewEditBtn = document.getElementById("see-visit-review-edit-btn");
    this.elements.seeVisitReviewCloseBtn = document.getElementById("see-visit-review-close-btn");
    
    this.elements.seeVisitReviewPrevBtn = document.getElementById("see-visit-review-prev-btn");
    this.elements.seeVisitReviewNextBtn = document.getElementById("see-visit-review-next-btn");
    this.elements.seeVisitReviewDotsContainer = document.getElementById("see-visit-review-dots-container");
    this.elements.carouselContainer = document.querySelector(".carousel-container");

    this.elements.actionPromptSection = document.getElementById("action-prompt-modal");
    this.elements.actionPromptTitle = document.getElementById("action-prompt-title");
    this.elements.actionPromptMessage = document.getElementById("action-prompt-message");
    this.elements.actionPromptConfirmBtn = document.getElementById("action-prompt-confirm-btn");
    this.elements.actionPromptCancelBtn = document.getElementById("action-prompt-cancel-btn");
  },

  setupEventListeners() {
    if (this.elements.seeVisitReviewCloseBtn) {
      this.elements.seeVisitReviewCloseBtn.addEventListener("click", () => this.hideSeeReviewModal());
    }

    if (this.elements.seeVisitReviewEditBtn) {
      this.elements.seeVisitReviewEditBtn.addEventListener("click", () => {
        if (this.currentVisitDataForReviewModal && this.editVisitReviewCallback) {
          const data = this.currentVisitDataForReviewModal;
          const name = this.currentPlaceNameForReviewModal;
          this.hideSeeReviewModal();
          this.editVisitReviewCallback(data, name);
        }
      });
    }

    if (this.elements.seeVisitReviewPrevBtn) {
      this.elements.seeVisitReviewPrevBtn.addEventListener("click", () => this.moveCarousel(-1));
    }
    if (this.elements.seeVisitReviewNextBtn) {
      this.elements.seeVisitReviewNextBtn.addEventListener("click", () => this.moveCarousel(1));
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
    try {
      console.log("Opening See Review Modal for visit:", visitDataInput);
      
      let visitData = typeof visitDataInput === "string"
          ? JSON.parse(visitDataInput)
          : visitDataInput;

      if (!visitData || !visitData.id) {
        console.error("Invalid visit data provided to showSeeReviewModal");
        return;
      }

      this.currentVisitDataForReviewModal = visitData;
      this.currentPlaceNameForReviewModal = placeName;
      const els = this.elements;

      if (!els.seeVisitReviewSection) {
        console.error("Critical Error: see-visit-review-section not found in DOM");
        alert("System error: Review dialog container missing.");
        return;
      }

      // Populate text fields with safety checks
      if (els.seeVisitReviewPlaceTitle) els.seeVisitReviewPlaceTitle.textContent = `"${placeName}"`;
      
      if (els.seeVisitReviewDateTime && visitData.visit_datetime) {
        const date = new Date(visitData.visit_datetime);
        els.seeVisitReviewDateTime.textContent = date.toLocaleString(undefined, {
          year: "numeric", month: "long", day: "numeric", 
          hour: "2-digit", minute: "2-digit"
        });
      }

      this.displayStaticRatingStars(els.seeVisitReviewRatingDisplay, visitData.rating);

      if (els.seeVisitReviewDisplayTitle) {
        els.seeVisitReviewDisplayTitle.textContent = visitData.review_title || "";
        els.seeVisitReviewDisplayTitle.style.display = visitData.review_title ? "block" : "none";
      }

      if (els.seeVisitReviewDisplayText) {
        els.seeVisitReviewDisplayText.textContent = visitData.review_text || 
          (visitData.rating ? "" : "(No review text)");
      }

      // Render photos using the carousel system
      this.renderReviewPhotos(visitData.photos || []);

      // Show the section
      els.seeVisitReviewSection.style.display = "block";
      els.seeVisitReviewSection.scrollIntoView({ behavior: "smooth", block: "center" });

    } catch (err) {
      console.error("Failed to show See Review modal:", err);
      alert("Error: Could not display review. See console for details.");
    }
  },

  renderReviewPhotos(photos) {
    const container = this.elements.seeVisitReviewPhotosContainer;
    const dotsContainer = this.elements.seeVisitReviewDotsContainer;
    const carouselWrapper = this.elements.carouselContainer;
    
    if (!container || !dotsContainer || !carouselWrapper) {
      console.warn("Carousel elements not found in review modal.");
      return;
    }

    container.innerHTML = "";
    dotsContainer.innerHTML = "";
    this.currentSlideIndex = 0;
    
    const validPhotos = (photos || []).filter(p => p.image_url);

    if (validPhotos.length === 0) {
      carouselWrapper.style.display = "none";
      return;
    }

    carouselWrapper.style.display = "block";
    
    // Sort: Main photo first
    const sortedPhotos = [...validPhotos].sort((a, b) => (b.is_main ? 1 : 0) - (a.is_main ? 1 : 0));
    this.totalSlides = sortedPhotos.length;

    // Visibility of arrows
    if (this.totalSlides <= 1) {
      if (this.elements.seeVisitReviewPrevBtn) this.elements.seeVisitReviewPrevBtn.style.display = "none";
      if (this.elements.seeVisitReviewNextBtn) this.elements.seeVisitReviewNextBtn.style.display = "none";
    } else {
      if (this.elements.seeVisitReviewPrevBtn) this.elements.seeVisitReviewPrevBtn.style.display = "flex";
      if (this.elements.seeVisitReviewNextBtn) this.elements.seeVisitReviewNextBtn.style.display = "flex";
    }

    sortedPhotos.forEach((photo, index) => {
      const img = document.createElement("img");
      img.src = photo.image_url;
      img.alt = "Visit photo";
      img.onerror = () => {
        console.error(`Failed to load image: ${photo.image_url}`);
        img.style.objectFit = "none";
        img.title = "Image failed to load";
      };
      img.addEventListener("click", (e) => this.showImageOverlay(e));
      container.appendChild(img);

      // Dots
      if (this.totalSlides > 1) {
        const dot = document.createElement("span");
        dot.className = "dot" + (index === 0 ? " active" : "");
        dot.addEventListener("click", () => this.goToSlide(index));
        dotsContainer.appendChild(dot);
      }
    });

    this.updateCarousel();
  },

  moveCarousel(direction) {
    this.currentSlideIndex += direction;
    if (this.currentSlideIndex >= this.totalSlides) this.currentSlideIndex = 0;
    if (this.currentSlideIndex < 0) this.currentSlideIndex = this.totalSlides - 1;
    this.updateCarousel();
  },

  goToSlide(index) {
    this.currentSlideIndex = index;
    this.updateCarousel();
  },

  updateCarousel() {
    const container = this.elements.seeVisitReviewPhotosContainer;
    const dots = this.elements.seeVisitReviewDotsContainer.querySelectorAll(".dot");
    
    if (container) {
      container.style.transform = `translateX(-${this.currentSlideIndex * 100}%)`;
    }
    
    dots.forEach((dot, idx) => {
      dot.classList.toggle("active", idx === this.currentSlideIndex);
    });
  },

  hideSeeReviewModal() {
    if (this.elements.seeVisitReviewSection) {
      this.elements.seeVisitReviewSection.style.display = "none";
    }
    this.currentVisitDataForReviewModal = null;
  },

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

    setTimeout(() => {
      if (this.elements.imageOverlayInstance) {
        this.elements.imageOverlayInstance.classList.add("visible");
      }
    }, 10);
  },

  hideImageOverlay() {
    const overlay = this.elements.imageOverlayInstance;
    if (!overlay) return;

    overlay.classList.remove("visible");
    overlay.addEventListener("transitionend", () => overlay.remove(), { once: true });
    this.elements.imageOverlayInstance = null;
  },

  /**
   * Reusable Action Prompt Modal (Used for Form Chaining)
   * @param {string} title 
   * @param {string} message 
   * @param {string} confirmText 
   * @param {string} cancelText 
   * @param {Function} onConfirm 
   * @param {Function} onCancel 
   */
  showActionPrompt(title, message, confirmText = "Yes", cancelText = "No", onConfirm, onCancel) {
    const els = this.elements;
    if (!els.actionPromptSection) return;

    // Reset Listeners by replacing nodes
    if (els.actionPromptConfirmBtn) {
        const newConfirm = els.actionPromptConfirmBtn.cloneNode(true);
        els.actionPromptConfirmBtn.parentNode.replaceChild(newConfirm, els.actionPromptConfirmBtn);
        els.actionPromptConfirmBtn = newConfirm;
    }
    if (els.actionPromptCancelBtn) {
        const newCancel = els.actionPromptCancelBtn.cloneNode(true);
        els.actionPromptCancelBtn.parentNode.replaceChild(newCancel, els.actionPromptCancelBtn);
        els.actionPromptCancelBtn = newCancel;
    }

    els.actionPromptTitle.textContent = title;
    els.actionPromptMessage.textContent = message;
    els.actionPromptConfirmBtn.textContent = confirmText;
    els.actionPromptCancelBtn.textContent = cancelText;

    els.actionPromptConfirmBtn.addEventListener("click", () => {
        els.actionPromptSection.style.display = "none";
        if (onConfirm) onConfirm();
    });

    els.actionPromptCancelBtn.addEventListener("click", () => {
        els.actionPromptSection.style.display = "none";
        if (onCancel) onCancel();
    });

    els.actionPromptSection.style.display = "block";
    els.actionPromptSection.scrollIntoView({ behavior: "smooth", block: "center" });
  },
};

export default modals;
