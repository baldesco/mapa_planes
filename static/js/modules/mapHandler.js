/**
 * mapHandler.js
 * Module for managing the Leaflet map instance and interactions.
 */

// Store map instance and related state locally within this module
let leafletMap = null;
let temporaryMarker = null;
let mapClickHandler = null;
let editMapClickHandler = null;
let isPinningModeActive = false; // General pinning flag for this module
let currentPinningFormType = null; // 'add' or 'edit'

// Callback functions to notify UI module about coordinate changes
let onCoordsUpdateCallback = null;
let onPinningModeChangeCallback = null;

const MAP_RETRY_DELAY = 300;
const MAX_MAP_RETRIES = 7; // Increased retries slightly

const mapHandler = {
  /**
   * Initialize the map handler. Tries to find the Leaflet map instance.
   * @param {function} onCoordsUpdate - Callback when coords change due to map interaction.
   * @param {function} onPinningChange - Callback when pinning mode starts/stops.
   * @returns {Promise<boolean>} - True if map found, false otherwise.
   */
  async init(onCoordsUpdate, onPinningChange) {
    onCoordsUpdateCallback = onCoordsUpdate;
    onPinningModeChangeCallback = onPinningChange;
    console.debug("Map Handler: Initializing...");
    leafletMap = await this.ensureMapReadyWithRetries();
    if (leafletMap) {
      console.log("Map Handler: Leaflet map instance obtained successfully.");
      // Add listener for popup open to potentially adjust view
      leafletMap.on("popupopen", function (e) {
        // console.debug('Popup opened:', e.popup);
        // Optional: Pan map slightly if popup is obscured?
      });
      return true;
    } else {
      console.error("Map Handler: Failed to obtain Leaflet map instance.");
      return false;
    }
  },

  /**
   * Tries to find the Leaflet map instance within the #map container.
   * Uses recursion to search child elements.
   * @param {HTMLElement} element - The current element to search within.
   * @returns {L.Map | null} - The Leaflet map instance or null.
   */
  findLeafletMapInstance(element) {
    if (!element) return null;
    // Check if the element itself is the map instance (less common now)
    // Leaflet often stores it on a child or via a property
    if (element._leaflet_map) {
      return element._leaflet_map;
    }
    // Check common Leaflet container class
    if (
      element.classList?.contains("leaflet-container") &&
      element.__leaflet_id
    ) {
      // Accessing via internal property is fragile, but sometimes necessary
      // A better approach is the global variable set by the Python template injection
      if (window.leafletMapInstance) {
        console.debug("Found map via injected global variable.");
        return window.leafletMapInstance;
      }
      console.warn(
        "Found .leaflet-container, but couldn't get instance directly. Relying on global."
      );
      // Fallback or alternative check might be needed depending on Folium/Leaflet version
    }

    // Recursively search children
    for (let i = 0; i < element.children.length; i++) {
      const childMap = this.findLeafletMapInstance(element.children[i]);
      if (childMap) {
        return childMap;
      }
    }
    return null;
  },

  /**
   * Attempts to get the map instance, retrying if necessary.
   * @param {number} retryCount - Current retry attempt number.
   * @returns {Promise<L.Map | null>} - The map instance or null after retries.
   */
  async ensureMapReadyWithRetries(retryCount = 0) {
    // Prefer the globally injected variable if available
    if (window.leafletMapInstance) {
      // console.debug("Using globally injected map instance.");
      leafletMap = window.leafletMapInstance; // Store it locally too
      return leafletMap;
    }

    // Fallback: search the DOM
    const mapDiv = document.getElementById("map");
    if (mapDiv) {
      leafletMap = this.findLeafletMapInstance(mapDiv);
      if (leafletMap) {
        console.debug("Found map instance by searching DOM.");
        return leafletMap;
      }
    }

    if (retryCount >= MAX_MAP_RETRIES) {
      console.error(`Map instance not found after ${MAX_MAP_RETRIES} retries.`);
      return null;
    }

    console.log(
      `Map not ready, retrying in ${MAP_RETRY_DELAY}ms (attempt ${
        retryCount + 1
      })`
    );
    await new Promise((resolve) => setTimeout(resolve, MAP_RETRY_DELAY));
    return this.ensureMapReadyWithRetries(retryCount + 1);
  },

  /**
   * Gets the currently stored map instance.
   * @returns {L.Map | null}
   */
  getMap() {
    if (!leafletMap && window.leafletMapInstance) {
      leafletMap = window.leafletMapInstance; // Ensure local copy is updated
    }
    return leafletMap;
  },

  /**
   * Enters map pinning mode for a specific form type ('add' or 'edit').
   * @param {string} formType - 'add' or 'edit'.
   * @param {object|null} initialCoords - Optional {lat, lng} to place initial marker for 'edit'.
   */
  startPinningMode(formType, initialCoords = null) {
    if (!leafletMap) {
      console.error("Cannot start pinning: Map not available.");
      return;
    }
    if (isPinningModeActive) {
      console.warn("Pinning mode already active. Cannot start again.");
      return; // Or potentially switch modes? For now, just prevent nesting.
    }

    console.log(`Map Handler: Entering pinning mode for form '${formType}'.`);
    isPinningModeActive = true;
    currentPinningFormType = formType;

    const mapContainer = leafletMap.getContainer();
    mapContainer.style.cursor = "crosshair";

    // Remove previous handlers if any exist
    if (mapClickHandler) leafletMap.off("click", mapClickHandler);
    if (editMapClickHandler) leafletMap.off("click", editMapClickHandler);

    // Add the correct handler
    const handler = (e) => this.handleMapClick(e, currentPinningFormType);
    if (formType === "add") {
      mapClickHandler = handler;
      leafletMap.on("click", mapClickHandler);
    } else {
      // 'edit'
      editMapClickHandler = handler;
      leafletMap.on("click", editMapClickHandler);
      // Place initial marker if coords provided for edit mode
      if (initialCoords && initialCoords.lat && initialCoords.lng) {
        this.placeTemporaryMarker(initialCoords.lat, initialCoords.lng);
      } else {
        console.warn("Edit pinning started without initial coordinates.");
      }
    }

    // Notify UI module
    if (onPinningModeChangeCallback) {
      onPinningModeChangeCallback(true, formType);
    }
  },

  /**
   * Exits map pinning mode.
   */
  stopPinningMode() {
    if (!isPinningModeActive || !leafletMap) {
      return; // Not in pinning mode or map not ready
    }

    console.log(
      `Map Handler: Exiting pinning mode (was for '${currentPinningFormType}').`
    );
    const mapContainer = leafletMap.getContainer();
    mapContainer.style.cursor = ""; // Reset cursor

    // Remove the active handler
    if (mapClickHandler) {
      leafletMap.off("click", mapClickHandler);
      mapClickHandler = null;
    }
    if (editMapClickHandler) {
      leafletMap.off("click", editMapClickHandler);
      editMapClickHandler = null;
    }

    // Remove the temporary marker
    this.removeTemporaryMarker();

    isPinningModeActive = false;
    const previousFormType = currentPinningFormType;
    currentPinningFormType = null;

    // Notify UI module
    if (onPinningModeChangeCallback) {
      onPinningModeChangeCallback(false, previousFormType);
    }
  },

  /**
   * Handles clicks on the map during pinning mode.
   * @param {L.LeafletMouseEvent} e - The Leaflet map click event.
   * @param {string} formType - The form type ('add' or 'edit') this click is for.
   */
  handleMapClick(e, formType) {
    if (!isPinningModeActive || formType !== currentPinningFormType) return; // Ensure correct mode/type

    const { lat, lng } = e.latlng;
    console.debug(`Map clicked at [${lat}, ${lng}] for form '${formType}'`);
    this.placeTemporaryMarker(lat, lng);
    this.updateCoordsFromPin({ latitude: lat, longitude: lng });
  },

  /**
   * Places or updates the temporary marker used for pinning.
   * @param {number} lat - Latitude.
   * @param {number} lng - Longitude.
   */
  placeTemporaryMarker(lat, lng) {
    if (!leafletMap) {
      console.error("Cannot place marker: Map instance not available.");
      return;
    }

    if (temporaryMarker) {
      // If marker exists, just update its position and popup
      temporaryMarker.setLatLng([lat, lng]).openPopup();
    } else {
      // Create new marker if it doesn't exist
      temporaryMarker = L.marker([lat, lng], { draggable: true })
        .addTo(leafletMap)
        .bindPopup("Selected Location. Drag to adjust.")
        .openPopup();

      // Add dragend event listener only once
      temporaryMarker.on("dragend", (event) => {
        if (!isPinningModeActive) return; // Only update if still pinning
        const marker = event.target;
        const position = marker.getLatLng();
        console.debug(
          `Temporary marker dragged to [${position.lat}, ${position.lng}]`
        );
        this.updateCoordsFromPin({
          latitude: position.lat,
          longitude: position.lng,
        });
        marker.setLatLng(position).openPopup(); // Update marker position visually
      });
    }
    // Pan map to center the marker
    leafletMap.setView([lat, lng]);
  },

  /**
   * Removes the temporary marker from the map.
   */
  removeTemporaryMarker() {
    if (temporaryMarker && leafletMap) {
      leafletMap.removeLayer(temporaryMarker);
      temporaryMarker = null;
      console.debug("Temporary marker removed.");
    }
  },

  /**
   * Notifies the UI module about new coordinates from map interaction.
   * @param {object} coords - Object with { latitude, longitude }.
   */
  updateCoordsFromPin(coords) {
    if (onCoordsUpdateCallback && currentPinningFormType) {
      // Pass coordinates and the form type they belong to
      onCoordsUpdateCallback(coords, currentPinningFormType);
    } else {
      console.warn(
        "Cannot update coords from pin: Callback or form type missing."
      );
    }
  },

  /**
   * Pans and zooms the map to a specific location.
   * @param {number} lat - Latitude.
   * @param {number} lng - Longitude.
   * @param {number} [zoomLevel=15] - Optional zoom level.
   */
  flyTo(lat, lng, zoomLevel = 15) {
    if (leafletMap && lat != null && lng != null) {
      leafletMap.flyTo([lat, lng], zoomLevel);
      console.debug(`Map flying to [${lat}, ${lng}] zoom ${zoomLevel}`);
    } else {
      console.warn(
        `Cannot flyTo: Map not ready or invalid coords [${lat}, ${lng}]`
      );
    }
  },
};

export default mapHandler;
