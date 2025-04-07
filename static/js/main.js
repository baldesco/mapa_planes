/**
 * main.js
 * Entry point for application-specific JavaScript.
 * Initializes modules and orchestrates interactions.
 */

import apiClient from "./modules/apiClient.js";
import auth from "./modules/auth.js";
import mapHandler from "./modules/mapHandler.js";
import ui from "./modules/ui.js";

document.addEventListener("DOMContentLoaded", async () => {
  console.log("DOM Loaded. Initializing main application script...");

  // Add class to body based on page for CSS targeting
  const pathname = window.location.pathname;
  if (pathname === "/login" || pathname === "/signup") {
    document.body.classList.add("auth-page");
  }

  // Initialize the UI module first
  ui.init(); // ui.init caches elements and sets initial state

  if (pathname === "/login") {
    auth.initLoginPage();
  } else if (pathname === "/signup") {
    auth.initSignupPage();
  } else if (pathname === "/") {
    console.log("On main map page, initializing map handler.");

    // Initialize map handler - needed for flyTo and placing draggable marker
    const mapReady = await mapHandler.init();

    if (!mapReady) {
      console.error(
        "Map initialization failed. Map-related functionality (geocoding flyTo, pinning) might be affected."
      );
      // Optionally disable buttons that rely heavily on the map
      if (ui.elements.addFindCoordsBtn)
        ui.elements.addFindCoordsBtn.disabled = true;
      if (ui.elements.editFindCoordsBtn)
        ui.elements.editFindCoordsBtn.disabled = true;
      if (ui.elements.addPinOnMapBtn)
        ui.elements.addPinOnMapBtn.disabled = true;
      if (ui.elements.editPinOnMapBtn)
        ui.elements.editPinOnMapBtn.disabled = true;
      ui.setStatusMessage(
        ui.elements.addGeocodeStatus,
        "Map failed to load. Location features disabled.",
        "error"
      );
      ui.setStatusMessage(
        ui.elements.editGeocodeStatus,
        "Map failed to load. Location features disabled.",
        "error"
      );
    } else {
      console.log("Map Handler initialized successfully.");
      // Buttons are enabled by default in ui.init, no need to re-enable here
    }

    auth.setupLogoutButton();
  } else {
    console.log(`On page ${pathname}, no specific page script to run.`);
    // Still set up logout if the button might exist on other potential pages
    auth.setupLogoutButton();
  }

  console.log("Main application script initialization complete.");
});
