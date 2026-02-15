/**
 * mapHandler.js
 * Manages the main Leaflet map instance and the pinning map instance.
 * Handles marker rendering, map centering, and viewport updates.
 * Updated for SPA-Lite to maintain marker references.
 */
import mapMarkers from "./components/mapMarkers.js";

let mainLeafletMap = null;
let pinningLeafletMap = null;
let pinningDraggableMarker = null;
let markersLayer = null;
let markerMap = {}; // Tracks markers by place ID: { [id]: markerInstance }

const mapHandler = {
  /**
   * Initializes the main application map.
   */
  initMainMap(containerId, mapData) {
    console.debug("Map Handler: Initializing main native map...");

    const mapContainer = document.getElementById(containerId);
    if (!mapContainer) {
      console.error(`Map container #${containerId} not found.`);
      return false;
    }

    const { center, zoom } = mapData.config || {
      center: [4.711, -74.0721],
      zoom: 12,
    };

    try {
      if (mainLeafletMap) {
        mainLeafletMap.remove();
      }

      mainLeafletMap = L.map(containerId).setView(center, zoom);

      L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
        attribution:
          '© <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
      }).addTo(mainLeafletMap);

      markersLayer = L.layerGroup().addTo(mainLeafletMap);

      if (mapData.places && mapData.places.length > 0) {
        this.renderMarkers(mapData.places);
      }

      console.log("Map Handler: Main native map initialized.");
      return true;
    } catch (error) {
      console.error("Map Handler: Error initializing main map:", error);
      return false;
    }
  },

  /**
   * Synchronizes the map markers with the provided list of places.
   * Clears existing markers and rebuilds the layer.
   */
  renderMarkers(places) {
    if (!mainLeafletMap || !markersLayer) return;

    // Clear existing layer and internal map
    markersLayer.clearLayers();
    markerMap = {};

    places.forEach((place) => {
      if (place.latitude != null && place.longitude != null) {
        const icon = mapMarkers.createIcon(place.category, place.status);
        const popupElement = mapMarkers.createPopupContainer(place);

        const marker = L.marker([place.latitude, place.longitude], {
          icon: icon,
        });

        marker.bindPopup(popupElement, { maxWidth: 300 });
        marker.bindTooltip(place.name || "Unnamed Place");

        markersLayer.addLayer(marker);
        markerMap[place.id] = marker;
      }
    });
  },

  /**
   * Returns the marker instance for a specific place ID.
   */
  getMarkerById(placeId) {
    return markerMap[placeId] || null;
  },

  getMainMap() {
    return mainLeafletMap;
  },

  flyTo(lat, lng, zoomLevel = 15) {
    if (mainLeafletMap && lat != null && lng != null) {
      mainLeafletMap.flyTo([lat, lng], zoomLevel);
    }
  },

  invalidateMapSize() {
    if (mainLeafletMap) {
      mainLeafletMap.invalidateSize({ animate: false });
    }
    if (pinningLeafletMap) {
      pinningLeafletMap.invalidateSize({ animate: false });
    }
  },

  // --- Pinning Map Logic ---

  initPinningMap(containerId = "pinning-map", initialCoords = null) {
    if (pinningLeafletMap) {
      this.destroyPinningMap();
    }

    const mapContainer = document.getElementById(containerId);
    if (!mapContainer) return false;

    try {
      let center = [4.711, -74.0721];
      let zoom = 13;

      if (initialCoords?.lat && initialCoords?.lng) {
        center = [initialCoords.lat, initialCoords.lng];
        zoom = 16;
      } else if (mainLeafletMap) {
        center = mainLeafletMap.getCenter();
        zoom = mainLeafletMap.getZoom();
      }

      pinningLeafletMap = L.map(containerId).setView(center, zoom);
      L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png").addTo(
        pinningLeafletMap,
      );

      setTimeout(() => pinningLeafletMap?.invalidateSize(), 100);
      return true;
    } catch (error) {
      console.error("Error initializing pinning map:", error);
      return false;
    }
  },

  placeDraggableMarker(initialCoords = null) {
    if (!pinningLeafletMap) return;

    this.removeDraggableMarker();

    const markerPosition =
      initialCoords?.lat && initialCoords?.lng
        ? [initialCoords.lat, initialCoords.lng]
        : pinningLeafletMap.getCenter();

    const icon = L.divIcon({
      html: '<i class="fas fa-map-pin fa-3x" style="color: #D32F2F;"></i>',
      className: "draggable-pin-icon",
      iconSize: [30, 42],
      iconAnchor: [15, 42],
    });

    pinningDraggableMarker = L.marker(markerPosition, {
      draggable: true,
      icon: icon,
      riseOnHover: true,
    }).addTo(pinningLeafletMap);

    pinningDraggableMarker.bindTooltip("Drag to location").openTooltip();
  },

  removeDraggableMarker() {
    if (pinningDraggableMarker && pinningLeafletMap) {
      pinningLeafletMap.removeLayer(pinningDraggableMarker);
      pinningDraggableMarker = null;
    }
  },

  getDraggableMarkerPosition() {
    return pinningDraggableMarker ? pinningDraggableMarker.getLatLng() : null;
  },

  destroyPinningMap() {
    this.removeDraggableMarker();
    if (pinningLeafletMap) {
      pinningLeafletMap.remove();
      pinningLeafletMap = null;
    }
  },
};

export default mapHandler;
