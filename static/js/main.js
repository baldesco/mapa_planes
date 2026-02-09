/**
 * main.js
 * Entry point for application-specific JavaScript.
 * Initializes core modules and sets up global hooks for SPA-lite behavior.
 */

import auth from "./modules/auth.js";
import uiOrchestrator from "./modules/uiOrchestrator.js";
import passwordReset from "./modules/passwordReset.js";

document.addEventListener("DOMContentLoaded", () => {
  console.debug("DOM Loaded. Initializing application modules...");

  const pathname = window.location.pathname;

  // Apply styling class for authentication-related pages
  const authRoutes = [
    "/login",
    "/signup",
    "/request-password-reset",
    "/reset-password",
  ];

  if (authRoutes.includes(pathname)) {
    document.body.classList.add("auth-page");
  }

  // Route-based initialization
  if (pathname === "/login") {
    auth.initLoginPage();
  } else if (pathname === "/signup") {
    auth.initSignupPage();
  } else if (pathname === "/request-password-reset") {
    passwordReset.initRequestPage();
  } else if (pathname === "/reset-password") {
    passwordReset.initResetPage();
  } else if (pathname === "/") {
    console.debug("Initializing Dashboard UI Orchestrator...");

    // Initialize the main UI system
    uiOrchestrator.init();

    // Setup the global logout handler
    auth.setupLogoutButton();

    /**
     * Global bridge for asynchronous components.
     * Used by mapMarkers.js to notify the orchestrator when a place is
     * deleted via the AJAX popup button.
     */
    window.handlePlaceDeleted = (placeId) => {
      console.debug(
        `Global Hook: Place ${placeId} deleted. Updating local state...`,
      );

      // Remove from the master list in orchestrator state
      uiOrchestrator.state.allPlaces = uiOrchestrator.state.allPlaces.filter(
        (p) => p.id !== placeId,
      );

      // Re-apply existing filters to the updated list and refresh the view
      uiOrchestrator.applyFilters();
    };
  } else {
    auth.setupLogoutButton();
  }

  console.debug("Application initialization complete.");
});
