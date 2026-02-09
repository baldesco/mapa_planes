/**
 * mapMarkers.js
 * Handles the creation of Leaflet icons and popup content for map markers.
 * Now uses DOM elements for popups to ensure robust event handling.
 */

const mapMarkers = {
  categoryIcons: {
    restaurant: "utensils",
    entertainment: "film",
    park: "tree",
    shopping: "shopping-cart",
    trip: "plane",
    other: "map-marker-alt",
  },

  statusColors: {
    visited: "green",
    pending_prioritized: "orange",
    pending: "blue",
    pending_scheduled: "purple",
  },

  /**
   * Creates a Leaflet icon based on place category and status.
   */
  createIcon(category, status) {
    const iconName = this.categoryIcons[category] || "info-circle";
    const markerColor = this.statusColors[status] || "gray";

    return L.divIcon({
      html: `<div class="leaflet-marker-icon-wrapper ${markerColor}">
                     <i class="fas fa-${iconName}"></i>
                   </div>`,
      className: "custom-leaflet-marker",
      iconSize: [30, 42],
      iconAnchor: [15, 42],
      popupAnchor: [0, -40],
    });
  },

  /**
   * Generates a DOM element for a place popup with attached event listeners.
   * @param {Object} place - The place data object.
   * @returns {HTMLElement} The popup container.
   */
  createPopupContainer(place) {
    const container = document.createElement("div");
    container.className = "map-popup-container";

    const name = this.escapeHtml(place.name || "Unnamed Place");
    const categoryLabel = this.escapeHtml(
      place.category.replace("_", " "),
    ).toUpperCase();
    const statusLabel = this.escapeHtml(
      place.status.replace("_", " "),
    ).toUpperCase();

    const addressParts = [place.address, place.city, place.country].filter(
      Boolean,
    );
    const addressInfo = addressParts.map((p) => this.escapeHtml(p)).join(", ");

    const tagsHtml =
      place.tags && place.tags.length > 0
        ? `<div class="popup-tags-container">
                <b>Tags:</b> 
                ${place.tags.map((t) => `<span class="popup-tag">${this.escapeHtml(t.name || t)}</span>`).join("")}
               </div>`
        : "";

    const now = new Date();
    const numFutureVisits = place.visits
      ? place.visits.filter((v) => new Date(v.visit_datetime) >= now).length
      : 0;

    let visitInfo = "No visits recorded yet.";
    if (numFutureVisits > 0) {
      visitInfo = `${numFutureVisits} upcoming visit(s) scheduled.`;
    } else if (place.visits && place.visits.length > 0) {
      visitInfo = `${place.visits.length} past visit(s) recorded.`;
    }

    container.innerHTML = `
            <h4>${name}</h4>
            <div class="popup-content-scrollable">
                <p><b>Category:</b> ${categoryLabel}</p>
                <p><b>Status:</b> ${statusLabel}</p>
                ${addressInfo ? `<p><b>Address:</b> ${addressInfo}</p>` : ""}
                ${tagsHtml}
            </div>
            <div class="popup-visits-info">
                ${visitInfo}
            </div>
            <div class="popup-actions">
                <button type="button" class="popup-btn-edit-place" id="btn-edit-${place.id}" title="Edit Place Details">Edit</button>
                <button type="button" class="popup-btn-plan-visit" id="btn-plan-${place.id}" title="Plan a New Visit">Plan</button>
                <button type="button" class="popup-btn-view-visits" id="btn-visits-${place.id}" title="View All Visits">Visits</button>
                <form action="/places/${place.id}/delete" method="post" 
                    onsubmit="return confirm('Delete this place and all its visits?');">
                    <button type="submit" class="popup-btn-delete-place" title="Delete Place">Delete</button>
                </form>
            </div>
        `;

    // Attach event listeners directly to the DOM elements
    container
      .querySelector(`#btn-edit-${place.id}`)
      .addEventListener("click", () => {
        if (window.showEditPlaceForm) window.showEditPlaceForm(place);
      });

    container
      .querySelector(`#btn-plan-${place.id}`)
      .addEventListener("click", () => {
        if (window.showPlanVisitForm) window.showPlanVisitForm(place);
      });

    container
      .querySelector(`#btn-visits-${place.id}`)
      .addEventListener("click", () => {
        if (window.showVisitsListModal) window.showVisitsListModal(place);
      });

    return container;
  },

  /**
   * Simple HTML escaping to prevent XSS.
   */
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

export default mapMarkers;
