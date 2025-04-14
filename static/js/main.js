/**
 * Entry point for application-specific JavaScript.
 * Initializes core modules based on the current page.
 */

import auth from "./modules/auth.js";
import mapHandler from "./modules/mapHandler.js";
import uiOrchestrator from "./modules/uiOrchestrator.js";
import passwordReset from "./modules/passwordReset.js";

document.addEventListener("DOMContentLoaded", async () => {
  console.log("DOM Loaded. Initializing main application script...");

  const pathname = window.location.pathname;

  // Add class to body for CSS targeting (e.g., auth pages)
  if (
    pathname === "/login" ||
    pathname === "/signup" ||
    pathname === "/request-password-reset" ||
    pathname === "/reset-password"
  ) {
    document.body.classList.add("auth-page");
  }

  // Initialize based on page
  if (pathname === "/login") {
    auth.initLoginPage();
  } else if (pathname === "/signup") {
    auth.initSignupPage();
  } else if (pathname === "/request-password-reset") {
    passwordReset.initRequestPage();
  } else if (pathname === "/reset-password") {
    // Initialization now happens directly in passwordReset.js after checking for supabase client
    passwordReset.initResetPage();
  } else if (pathname === "/") {
    console.log("Initializing core modules for main page.");
    const mapReady = await mapHandler.init();
    uiOrchestrator.init(mapReady);
    auth.setupLogoutButton();
  } else {
    // Setup logout button if it might exist on other potential pages
    auth.setupLogoutButton();
  }

  console.log("Main application script initialization complete.");
});
