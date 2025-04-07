/**
 * Entry point for application-specific JavaScript.
 * Initializes core modules based on the current page.
 */

import auth from "./modules/auth.js";
import mapHandler from "./modules/mapHandler.js";
import uiOrchestrator from "./modules/uiOrchestrator.js"; // Import the new orchestrator

document.addEventListener("DOMContentLoaded", async () => {
  console.log("DOM Loaded. Initializing main application script...");

  const pathname = window.location.pathname;

  // Add class to body for CSS targeting (e.g., auth pages)
  if (pathname === "/login" || pathname === "/signup") {
    document.body.classList.add("auth-page");
  }

  // Initialize based on page
  if (pathname === "/login") {
    auth.initLoginPage();
  } else if (pathname === "/signup") {
    auth.initSignupPage();
  } else if (pathname === "/") {
    console.log("On main map page, initializing core modules.");

    // Initialize map handler first (essential for map features)
    const mapReady = await mapHandler.init();

    // Initialize the UI orchestrator, passing map status
    uiOrchestrator.init(mapReady);

    // Setup logout button (could be moved into uiOrchestrator if preferred)
    auth.setupLogoutButton();
  } else {
    console.log(`On page ${pathname}, no specific page script to run.`);
    // Setup logout button if it might exist on other potential pages
    auth.setupLogoutButton();
  }

  console.log("Main application script initialization complete.");
});
