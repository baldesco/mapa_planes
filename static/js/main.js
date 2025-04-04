/**
 * main.js
 * Entry point for application-specific JavaScript.
 * Initializes modules and orchestrates interactions.
 */

// Import modules
import apiClient from "./modules/apiClient.js";
import auth from "./modules/auth.js";
import mapHandler from "./modules/mapHandler.js";
import ui from "./modules/ui.js";

document.addEventListener("DOMContentLoaded", async () => {
  console.log("DOM Loaded. Initializing main application script...");

  // Initialize the UI module first to cache elements and setup basic listeners
  ui.init();

  // Determine current page to initialize relevant scripts
  const pathname = window.location.pathname;

  if (pathname === "/login") {
    console.log("On login page, initializing auth login script.");
    auth.initLoginPage();
  } else if (pathname === "/signup") {
    console.log("On signup page, initializing auth signup script.");
    auth.initSignupPage();
  } else if (pathname === "/") {
    console.log("On main map page, initializing map and UI handlers.");

    // Initialize map handler, providing UI callbacks
    const mapReady = await mapHandler.init(
      ui.handleCoordsUpdateFromMap.bind(ui), // Pass UI method as callback
      ui.handlePinningModeChange.bind(ui) // Pass UI method as callback
    );

    if (!mapReady) {
      // Display an error to the user if the map fails to load
      // ui.setStatusMessage(someErrorElement, "Failed to load map.", "error");
      console.error(
        "Map initialization failed. Some features may be unavailable."
      );
      // Consider disabling map-dependent buttons
      if (ui.elements.addPinOnMapBtn)
        ui.elements.addPinOnMapBtn.disabled = true;
      if (ui.elements.editPinOnMapBtn)
        ui.elements.editPinOnMapBtn.disabled = true;
    }

    // Setup logout button listener (might be on the main page)
    auth.setupLogoutButton();
  } else {
    console.log(`On page ${pathname}, no specific page script to run.`);
    // Setup logout button listener if it exists on other potential pages
    auth.setupLogoutButton();
  }

  console.log("Main application script initialization complete.");
});

// Note: Functions previously exposed globally via `window.someFunction = ...`
// are now handled within the ui.js module initialization.
// The inline `onclick` attributes in the HTML still call these globally exposed functions.
// A further refactor could involve replacing all `onclick` attributes with
// event listeners set up within the relevant modules (e.g., using event delegation).
