/**
 * mapMarkers.js
 * Handles the creation of Leaflet icons and popup content.
 */
import apiClient from "../apiClient.js";

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

  createPopupContainer(place) {
    const container = document.createElement("div");
    container.className = "map-popup-container";

    const addressParts = [place.address, place.city].filter(Boolean);
    const addressInfo = addressParts.map((p) => this.escapeHtml(p)).join(", ");

    container.innerHTML = `
            <h4>${this.escapeHtml(place.name)}</h4>
            <div class="popup-content-scrollable">
                <p><b>Category:</b> ${this.escapeHtml(place.category).toUpperCase()}</p>
                ${addressInfo ? `<p><b>Address:</b> ${addressInfo}</p>` : ""}
            </div>
            <div class="popup-actions">
                <button type="button" class="popup-btn-edit-place" id="pop-edit-${place.id}">Edit</button>
                <button type="button" class="popup-btn-plan-visit" id="pop-plan-${place.id}">Plan</button>
                <button type="button" class="popup-btn-view-visits" id="pop-list-${place.id}">Visits</button>
                <button type="button" class="popup-btn-delete-place" id="pop-del-${place.id}">Delete</button>
            </div>
        `;

    // We use a listener on the container for event delegation to handle buttons
    container.addEventListener("click", (e) => {
      if (e.target.id === `pop-edit-${place.id}`)
        window.showEditPlaceForm(place);
      if (e.target.id === `pop-plan-${place.id}`)
        window.showPlanVisitForm(place);
      if (e.target.id === `pop-list-${place.id}`)
        window.showVisitsListModal(place);
      if (e.target.id === `pop-del-${place.id}`) this.handleDelete(place.id);
    });

    return container;
  },

  async handleDelete(placeId) {
    if (!confirm("Are you sure you want to delete this place?")) return;
    try {
      const response = await apiClient.delete(`/api/v1/places/${placeId}`);
      if (response.ok && window.handlePlaceDeleted) {
        window.handlePlaceDeleted(placeId);
      }
    } catch (error) {
      console.error("Delete failed", error);
    }
  },

  escapeHtml(unsafe) {
    if (!unsafe) return "";
    return String(unsafe).replace(
      /[&<>"']/g,
      (m) =>
        ({
          "&": "&amp;",
          "<": "&lt;",
          ">": "&gt;",
          '"': "&quot;",
          "'": "&#039;",
        })[m],
    );
  },
};

export default mapMarkers;
