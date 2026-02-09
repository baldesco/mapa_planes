/**
 * sidebar.js
 * Manages the rendering, searching, and sorting of the places list.
 */

const sidebar = {
  elements: {
    listContainer: null,
    countDisplay: null,
    searchInput: null,
    sortSelect: null,
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
    this.elements.searchInput = document.getElementById("global-search");
    this.elements.sortSelect = document.getElementById("sort-places");
  },

  setupEventListeners() {
    if (this.elements.listContainer) {
      // Event delegation for place card clicks
      this.elements.listContainer.addEventListener("click", (e) => {
        const card = e.target.closest(".place-card");
        if (card && this.onPlaceClickCallback) {
          const placeId = parseInt(card.dataset.id);
          this.setActiveCard(placeId);
          this.onPlaceClickCallback(placeId);
        }
      });
    }
  },

  /**
   * Renders the sidebar list based on the provided places array.
   */
  render(places) {
    if (!this.elements.listContainer) return;

    if (!places || places.length === 0) {
      this.elements.listContainer.innerHTML =
        '<div class="sidebar-empty">No places found matching your criteria.</div>';
      this.elements.countDisplay.textContent = "0";
      return;
    }

    this.elements.countDisplay.textContent = places.length;

    const html = places
      .map((place) => this.createPlaceCardHtml(place))
      .join("");
    this.elements.listContainer.innerHTML = html;
  },

  createPlaceCardHtml(place) {
    const ratingHtml =
      place.visits && place.visits.length > 0
        ? this.getRatingStarsHtml(place.visits[0].rating)
        : "";

    const tagsHtml =
      place.tags && place.tags.length > 0
        ? `<div class="place-card-tags">
                ${place.tags
                  .map(
                    (t) =>
                      `<span class="mini-tag">${this.escapeHtml(t.name || t)}</span>`,
                  )
                  .slice(0, 3)
                  .join("")}
               </div>`
        : "";

    const statusLabel = place.status.replace("_", " ");

    return `
            <div class="place-card" data-id="${place.id}">
                <div class="place-card-header">
                    <h3 class="place-card-title">${this.escapeHtml(place.name)}</h3>
                    <span class="place-card-category">${this.escapeHtml(place.category)}</span>
                </div>
                <div class="place-card-address">${this.escapeHtml(place.address || "No address set")}</div>
                ${tagsHtml}
                <div class="place-card-meta">
                    <span class="status-badge ${place.status}">${this.escapeHtml(statusLabel)}</span>
                    <div class="place-card-rating">${ratingHtml}</div>
                </div>
            </div>
        `;
  },

  getRatingStarsHtml(rating) {
    if (!rating) return "";
    let stars = "";
    for (let i = 0; i < 5; i++) {
      stars += `<i class="${i < rating ? "fas" : "far"} fa-star"></i>`;
    }
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
