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

  // Initialize the UI module first
  ui.init(); // ui.init now enables pin buttons by default

  const pathname = window.location.pathname;

  if (pathname === "/login") {
    auth.initLoginPage();
  } else if (pathname === "/signup") {
    auth.initSignupPage();
  } else if (pathname === "/") {
    console.log("On main map page, initializing map handler (for flyTo).");

    // Initialize map handler - primarily needed for flyTo now
    // Pinning click logic is handled via iframe -> parent communication
    const mapReady = await mapHandler.init(); // No callbacks needed for pinning

    if (!mapReady) {
      console.error(
        "Map initialization failed. flyTo functionality might be affected."
      );
      // Optionally disable geocode buttons if flyTo is essential for them
      // if (ui.elements.addFindCoordsBtn) ui.elements.addFindCoordsBtn.disabled = true;
      // if (ui.elements.editFindCoordsBtn) ui.elements.editFindCoordsBtn.disabled = true;
    } else {
      console.log("Map Handler initialized successfully (needed for flyTo).");
      // Buttons are enabled by ui.init regardless of mapReady status now
    }

    auth.setupLogoutButton();
  } else {
    console.log(`On page ${pathname}, no specific page script to run.`);
    auth.setupLogoutButton();
  }

  console.log("Main application script initialization complete.");
});
