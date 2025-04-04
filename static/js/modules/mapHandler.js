/**
 * mapHandler.js
 * Module for finding the Leaflet map instance and providing map actions like flyTo.
 * Pinning click logic is now handled by script injected into the iframe by mapping.py.
 */

let leafletMap = null;
// Removed state related to pinning mode, callbacks, click handlers

const MAP_RETRY_DELAY = 500;
const MAX_MAP_RETRIES = 12;

const mapHandler = {
  async init() {
    // No longer needs callbacks passed in
    console.debug("Map Handler: Initializing (for flyTo)...");
    try {
      leafletMap = await this.ensureMapReadyWithRetries();
      if (leafletMap) {
        console.log("Map Handler: Leaflet map instance obtained successfully.");
        return true;
      } else {
        console.error(
          "Map Handler: Failed to obtain Leaflet map instance after retries."
        );
        return false;
      }
    } catch (error) {
      console.error(
        "Map Handler: CRITICAL ERROR during initialization:",
        error
      );
      return false;
    }
  },

  // Recursive DOM search function
  findLeafletMapInstance(element) {
    if (!element) return null;
    if (element._leaflet_map) {
      // console.debug("findLeafletMapInstance: Found via _leaflet_map property");
      return element._leaflet_map;
    }
    // Recursive search
    for (let i = 0; i < element.children.length; i++) {
      const childMap = this.findLeafletMapInstance(element.children[i]);
      if (childMap) {
        // console.debug("findLeafletMapInstance: Found via child recursion");
        return childMap;
      }
    }
    return null;
  },

  async ensureMapReadyWithRetries(retryCount = 0) {
    try {
      const mapDiv = document.getElementById("map");
      if (mapDiv) {
        leafletMap = this.findLeafletMapInstance(mapDiv); // Update local ref
        if (leafletMap) {
          console.debug(
            `ensureMapReady: Found Leaflet instance via DOM search on attempt ${
              retryCount + 1
            }`
          );
          return leafletMap; // Return the found instance
        }
      } else {
        console.error("ensureMapReady: #map div not found in DOM!");
        return null;
      }

      if (retryCount >= MAX_MAP_RETRIES) {
        console.error(
          `ensureMapReady: Map instance not found attached to #map div after ${MAX_MAP_RETRIES} retries.`
        );
        return null;
      }

      console.log(
        `ensureMapReady: Map instance not found in #map div, retrying in ${MAP_RETRY_DELAY}ms (attempt ${
          retryCount + 1
        })`
      );
      await new Promise((resolve) => setTimeout(resolve, MAP_RETRY_DELAY));
      return this.ensureMapReadyWithRetries(retryCount + 1);
    } catch (error) {
      console.error(
        `ensureMapReady: Error during attempt ${retryCount + 1}:`,
        error
      );
      return null;
    }
  },

  getMap() {
    // Still useful to get the instance if needed elsewhere (like flyTo)
    return leafletMap;
  },

  // --- Pinning related methods removed ---
  // startPinningMode, stopPinningMode, handleMapClick, placeTemporaryMarker, removeTemporaryMarker, updateCoordsFromPin

  /** Pans and zooms the map to a specific location */
  flyTo(lat, lng, zoomLevel = 15) {
    // Use this.getMap() to ensure we have the latest reference
    const currentMap = this.getMap();
    if (currentMap && lat != null && lng != null) {
      currentMap.flyTo([lat, lng], zoomLevel);
      console.debug(`Map flying to [${lat}, ${lng}] zoom ${zoomLevel}`);
    } else {
      console.warn(
        `Cannot flyTo: Map not ready or invalid coords [${lat}, ${lng}]`
      );
    }
  },
};

export default mapHandler;
