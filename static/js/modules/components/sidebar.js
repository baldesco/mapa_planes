/**
 * sidebar.js
 * Manages the rendering and interaction of the places list.
 * Designed for SPA-lite state management.
 */

const sidebar = {
  elements: {
    listContainer: null,
    countDisplay: null,
  },
  onPlaceClickCallback: null,

  init(onPlaceClick) {
    this.onPlaceClickCallback = onPlaceClick;
    this.cacheDOMElements();
    this.setupEventListeners();
  },

  cacheDOMElements() {
    this.elements.listContainer = document.getElementById("places-list");
    this.elements.countDisplay = document.getElementById("places-count");
  },

  setupEventListeners() {
    if (!this.elements.listContainer) return;

    // Use event delegation for clicking place cards
    this.elements.listContainer.addEventListener("click", (e) => {
      const card = e.target.closest(".place-card");
      if (card && this.onPlaceClickCallback) {
        const placeId = parseInt(card.dataset.id);
        this.setActiveCard(placeId);
        this.onPlaceClickCallback(placeId);
      }
    });
  },

  /**
   * Renders the list of places based on current filtered/sorted state.
   */
  render(places) {
    if (!this.elements.listContainer) return;

    if (!places || places.length === 0) {
      this.elements.listContainer.innerHTML = `
                <div class="sidebar-empty">
                    <p>No places found.</p>
                </div>`;
      if (this.elements.countDisplay)
        this.elements.countDisplay.textContent = "0";
      return;
    }

    if (this.elements.countDisplay) {
      this.elements.countDisplay.textContent = places.length;
    }

    const html = places
      .map((place) => this.createPlaceCardHtml(place))
      .join("");
    this.elements.listContainer.innerHTML = html;
  },

  /**
   * Creates HTML string for a single place card.
   */
  createPlaceCardHtml(place) {
    const statusLabel = place.status.replace(/_/g, " ");

    // Logic to get latest rating from visits
    let ratingHtml = "";
    if (place.visits && place.visits.length > 0) {
      const lastRatedVisit = place.visits.find((v) => v.rating);
      if (lastRatedVisit) {
        ratingHtml = this.getRatingStarsHtml(lastRatedVisit.rating);
      }
    }

    const tagsHtml = (place.tags || [])
      .slice(0, 3)
      .map(
        (t) => `<span class="mini-tag">${this.escapeHtml(t.name || t)}</span>`,
      )
      .join("");

    return `
            <div class="place-card" data-id="${place.id}">
                <div class="place-card-header">
                    <h3 class="place-card-title">${this.escapeHtml(place.name)}</h3>
                    <span class="place-card-category">${this.escapeHtml(place.category)}</span>
                </div>
                <div class="place-card-address">${this.escapeHtml(place.address || "Location on map")}</div>
                <div class="place-card-tags">${tagsHtml}</div>
                <div class="place-card-meta">
                    <span class="status-badge ${place.status}">${this.escapeHtml(statusLabel)}</span>
                    <div class="place-card-rating">${ratingHtml}</div>
                </div>
            </div>
        `;
  },

  getRatingStarsHtml(rating) {
    let stars = '<div class="rating-stars-display">';
    for (let i = 1; i <= 5; i++) {
      stars += `<i class="${i <= rating ? "fas" : "far"} fa-star"></i>`;
    }
    stars += "</div>";
    return stars;
  },

  setActiveCard(placeId) {
    const cards = this.elements.listContainer.querySelectorAll(".place-card");
    cards.forEach((card) => {
      if (parseInt(card.dataset.id) === placeId) {
        card.classList.add("active");
        card.scrollIntoView({ behavior: "smooth", block: "nearest" });
      } else {
        card.classList.remove("active");
      }
    });
  },

  escapeHtml(unsafe) {
    if (!unsafe) return "";
    return String(unsafe)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#039;");
  },
};

export default sidebar;
