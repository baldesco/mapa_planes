/**
 * mapMarkers.js
 * Handles the creation of Leaflet icons and popup content for map markers.
 * Updated to use AJAX for deletions and SPA-lite interactions.
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

  /**
   * Generates a DOM element for a place popup.
   * Uses internal buttons instead of forms to support SPA-lite behavior.
   */
  createPopupContainer(place) {
    const container = document.createElement("div");
    container.className = "map-popup-container";

    const name = this.escapeHtml(place.name || "Unnamed Place");
    const categoryLabel = this.escapeHtml(place.category).toUpperCase();

    const addressParts = [place.address, place.city].filter(Boolean);
    const addressInfo = addressParts.map((p) => this.escapeHtml(p)).join(", ");

    const now = new Date();
    const numFutureVisits = place.visits
      ? place.visits.filter((v) => new Date(v.visit_datetime) >= now).length
      : 0;

    container.innerHTML = `
            <h4>${name}</h4>
            <div class="popup-content-scrollable">
                <p><b>Category:</b> ${categoryLabel}</p>
                ${addressInfo ? `<p><b>Address:</b> ${addressInfo}</p>` : ""}
                <div class="popup-tags-container">
                    ${(place.tags || []).map((t) => `<span class="popup-tag">${this.escapeHtml(t.name || t)}</span>`).join("")}
                </div>
            </div>
            <div class="popup-visits-info">
                ${numFutureVisits > 0 ? `${numFutureVisits} upcoming visits` : "No upcoming visits"}
            </div>
            <div class="popup-actions">
                <button type="button" class="popup-btn-edit-place" id="pop-edit-${place.id}">Edit</button>
                <button type="button" class="popup-btn-plan-visit" id="pop-plan-${place.id}">Plan</button>
                <button type="button" class="popup-btn-view-visits" id="pop-list-${place.id}">Visits</button>
                <button type="button" class="popup-btn-delete-place" id="pop-del-${place.id}">Delete</button>
            </div>
        `;

    // Attach listeners after the HTML is set
    setTimeout(() => {
      container.querySelector(`#pop-edit-${place.id}`).onclick = () =>
        window.showEditPlaceForm(place);
      container.querySelector(`#pop-plan-${place.id}`).onclick = () =>
        window.showPlanVisitForm(place);
      container.querySelector(`#pop-list-${place.id}`).onclick = () =>
        window.showVisitsListModal(place);
      container.querySelector(`#pop-del-${place.id}`).onclick = () =>
        this.handleDelete(place.id);
    }, 0);

    return container;
  },

  async handleDelete(placeId) {
    if (!confirm("Are you sure you want to delete this place?")) return;

    try {
      const response = await apiClient.delete(`/api/v1/places/${placeId}`);
      if (response.ok) {
        // Trigger global orchestrator event to update state and UI
        if (window.handlePlaceDeleted) {
          window.handlePlaceDeleted(placeId);
        } else {
          // Fallback if orchestrator isn't ready
          window.location.reload();
        }
      } else {
        alert("Failed to delete place.");
      }
    } catch (error) {
      console.error("Error deleting place:", error);
      alert("Connection error while deleting.");
    }
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

export default mapMarkers;
