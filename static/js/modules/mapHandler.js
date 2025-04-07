/**
 * mapHandler.js
 * Module for finding the main Leaflet map instance (from Folium)
 * and managing a separate Leaflet map instance for pinning locations.
 */

let mainLeafletMap = null; // Instance for the main map (Folium iframe)
let pinningLeafletMap = null; // Instance for the dedicated pinning map
let pinningDraggableMarker = null; // Draggable marker for the pinning map

const MAP_RETRY_DELAY = 500;
const MAX_MAP_RETRIES = 12;

const mapHandler = {
  async init() {
    console.debug("Map Handler: Initializing (finding main map)...");
    try {
      mainLeafletMap = await this.findMainMapInstanceWithRetries();
      if (mainLeafletMap) {
        console.log(
          "Map Handler: Main Leaflet map instance (Folium) obtained."
        );
        return true;
      } else {
        console.error(
          "Map Handler: Failed to obtain main map instance after retries."
        );
        return false;
      }
    } catch (error) {
      console.error(
        "Map Handler: CRITICAL ERROR during main map initialization:",
        error
      );
      return false;
    }
  },

  // --- Main Map (Folium Iframe) Logic ---

  findMainMapInstance(element) {
    // Same logic as before
    if (!element) return null;
    if (element._leaflet_map) return element._leaflet_map;
    const iframe = element.querySelector("iframe");
    if (iframe && iframe.contentWindow) {
      const L = iframe.contentWindow.L;
      if (L && L.Map) {
        const iframeMapDiv =
          iframe.contentWindow.document.querySelector(".leaflet-container");
        if (iframeMapDiv && iframeMapDiv._leaflet_map) {
          return iframeMapDiv._leaflet_map;
        }
        const potentialMapVarNames = Object.keys(iframe.contentWindow).filter(
          (k) => k.startsWith("map_")
        );
        for (const varName of potentialMapVarNames) {
          const mapInstance = iframe.contentWindow[varName];
          if (
            mapInstance &&
            typeof mapInstance.getCenter === "function" &&
            mapInstance instanceof L.Map
          ) {
            return mapInstance;
          }
        }
      }
    }
    for (let i = 0; i < element.children.length; i++) {
      if (element.children[i].tagName !== "IFRAME") {
        const childMap = this.findMainMapInstance(element.children[i]);
        if (childMap) return childMap;
      }
    }
    return null;
  },

  async findMainMapInstanceWithRetries(retryCount = 0) {
    // Same retry logic as before
    try {
      const mapDiv = document.getElementById("map");
      if (mapDiv) {
        const foundMap = this.findMainMapInstance(mapDiv);
        if (foundMap) {
          return foundMap;
        }
      } else {
        console.error("findMainMapInstanceWithRetries: #map div not found!");
        return null;
      }
      if (retryCount >= MAX_MAP_RETRIES) {
        console.error(
          `findMainMapInstanceWithRetries: Main map instance not found after ${
            MAX_MAP_RETRIES + 1
          } attempts.`
        );
        return null;
      }
      console.log(
        `findMainMapInstanceWithRetries: Main map not found yet, retrying in ${MAP_RETRY_DELAY}ms (attempt ${
          retryCount + 2
        })`
      );
      await new Promise((resolve) => setTimeout(resolve, MAP_RETRY_DELAY));
      return this.findMainMapInstanceWithRetries(retryCount + 1);
    } catch (error) {
      console.error(
        `findMainMapInstanceWithRetries: Error during attempt ${
          retryCount + 1
        }:`,
        error
      );
      return null;
    }
  },

  getMainMap() {
    // Same getter as before
    if (!mainLeafletMap) {
      console.warn(
        "getMainMap: mainLeafletMap is null, attempting to find again."
      );
      const mapDiv = document.getElementById("map");
      if (mapDiv) mainLeafletMap = this.findMainMapInstance(mapDiv);
    }
    return mainLeafletMap;
  },

  flyTo(lat, lng, zoomLevel = 15) {
    // Same flyTo for main map as before
    const currentMap = this.getMainMap();
    if (currentMap && lat != null && lng != null) {
      try {
        currentMap.flyTo([lat, lng], zoomLevel);
        console.debug(`Main Map flying to [${lat}, ${lng}] zoom ${zoomLevel}`);
      } catch (e) {
        console.error("Error during main map flyTo:", e);
        this.findMainMapInstanceWithRetries().then((map) => {
          if (map) {
            try {
              map.flyTo([lat, lng], zoomLevel);
            } catch (e2) {
              /* ignore */
            }
          }
        });
      }
    } else {
      console.warn(
        `Cannot flyTo main map: Map not ready or invalid coords [${lat}, ${lng}]`
      );
    }
  },

  // --- Pinning Map Logic ---

  /**
   * Initializes the dedicated pinning map.
   * @param {string} containerId - The ID of the div to contain the map.
   * @param {object|null} initialCoords - Optional {lat, lng} to center on initially.
   * @returns {boolean} - True if initialization was successful, false otherwise.
   */
  initPinningMap(containerId = "pinning-map", initialCoords = null) {
    if (pinningLeafletMap) {
      console.warn(
        "Pinning map already initialized. Destroying previous instance."
      );
      this.destroyPinningMap();
    }

    const mapContainer = document.getElementById(containerId);
    if (!mapContainer) {
      console.error(`Pinning map container #${containerId} not found.`);
      return false;
    }
    if (typeof L === "undefined" || !L.map) {
      console.error("Leaflet library (L) not found.");
      return false;
    }

    try {
      const defaultCenter = [4.711, -74.0721]; // Bogotá
      let center = defaultCenter;
      let zoom = 13;

      // Use provided initialCoords if valid
      if (
        initialCoords &&
        typeof initialCoords.lat === "number" &&
        typeof initialCoords.lng === "number"
      ) {
        center = [initialCoords.lat, initialCoords.lng];
        zoom = 16; // Zoom closer if starting at a specific point
        console.debug("Initializing pinning map at provided coords:", center);
      } else {
        // Fallback: Try to use main map's center/zoom
        const mainMap = this.getMainMap();
        if (mainMap) {
          try {
            center = mainMap.getCenter();
            zoom = mainMap.getZoom();
            console.debug(
              "Initializing pinning map at main map center:",
              center
            );
          } catch (e) {
            console.warn("Could not get center/zoom from main map.", e);
          }
        } else {
          console.debug("Initializing pinning map at default center.");
        }
      }

      pinningLeafletMap = L.map(containerId).setView(center, zoom);

      L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
        attribution:
          '© <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
      }).addTo(pinningLeafletMap);

      console.log(`Pinning map initialized in #${containerId}.`);
      // Invalidate size after a short delay to ensure correct rendering, especially if container was hidden
      setTimeout(() => {
        if (pinningLeafletMap) pinningLeafletMap.invalidateSize();
      }, 100);
      return true;
    } catch (error) {
      console.error("Error initializing pinning map:", error);
      pinningLeafletMap = null;
      return false;
    }
  },

  /**
   * Places a draggable marker on the pinning map.
   * @param {object|null} initialCoords - Optional {lat, lng} for initial marker position.
   */
  placeDraggableMarker(initialCoords = null) {
    if (!pinningLeafletMap) {
      console.error(
        "Cannot place draggable marker: Pinning map not initialized."
      );
      return;
    }
    if (typeof L === "undefined" || !L.divIcon || !L.marker) {
      console.error("Leaflet (L) or required components not available.");
      return;
    }

    this.removeDraggableMarker(); // Remove existing one first

    let markerPosition;
    // Use provided coords if valid, otherwise use map center
    if (
      initialCoords &&
      typeof initialCoords.lat === "number" &&
      typeof initialCoords.lng === "number"
    ) {
      markerPosition = [initialCoords.lat, initialCoords.lng];
      console.debug(
        "Placing draggable marker at provided initial coords:",
        markerPosition
      );
    } else {
      markerPosition = pinningLeafletMap.getCenter();
      console.debug(
        "Placing draggable marker at pinning map center:",
        markerPosition
      );
    }

    const icon = L.divIcon({
      html: '<i class="fas fa-map-pin fa-3x" style="color: #D32F2F; text-shadow: 1px 1px 3px rgba(0,0,0,0.5);"></i>',
      className: "draggable-pin-icon",
      iconSize: [30, 42],
      iconAnchor: [15, 42],
    });

    try {
      pinningDraggableMarker = L.marker(markerPosition, {
        draggable: true,
        icon: icon,
        riseOnHover: true,
      }).addTo(pinningLeafletMap);

      pinningDraggableMarker
        .bindTooltip("Drag me to the desired location!")
        .openTooltip();
      pinningDraggableMarker.on("dragend", () => {
        console.log("Pinning marker drag ended.");
        pinningDraggableMarker.openTooltip();
      });
      console.debug(`Placed draggable marker on pinning map.`);
    } catch (error) {
      console.error(
        "Error creating or adding draggable marker to pinning map:",
        error
      );
    }
  },

  removeDraggableMarker() {
    // Same as before
    if (pinningDraggableMarker && pinningLeafletMap) {
      try {
        pinningLeafletMap.removeLayer(pinningDraggableMarker);
        console.debug("Removed draggable marker from pinning map.");
      } catch (e) {
        console.error("Error removing draggable marker from pinning map:", e);
      } finally {
        pinningDraggableMarker = null;
      }
    }
  },

  getDraggableMarkerPosition() {
    // Same as before
    if (pinningDraggableMarker) {
      try {
        return pinningDraggableMarker.getLatLng();
      } catch (e) {
        console.error("Error getting pinning marker LatLng:", e);
        return null;
      }
    }
    return null;
  },

  destroyPinningMap() {
    // Same as before
    this.removeDraggableMarker();
    if (pinningLeafletMap) {
      try {
        pinningLeafletMap.remove();
        console.log("Pinning map instance destroyed.");
      } catch (e) {
        console.error("Error destroying pinning map:", e);
      } finally {
        pinningLeafletMap = null;
      }
    }
    const container = document.getElementById("pinning-map-container");
    if (container) container.style.display = "none";
  },
};

export default mapHandler;
