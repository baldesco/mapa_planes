/**
 * main.js
 * Entry point for application-specific JavaScript.
 * Initializes core modules based on the current page route.
 */

import auth from "./modules/auth.js";
import uiOrchestrator from "./modules/uiOrchestrator.js";
import passwordReset from "./modules/passwordReset.js";

document.addEventListener("DOMContentLoaded", () => {
  console.log("DOM Loaded. Initializing application modules...");

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
    // The main dashboard orchestration
    console.log("Initializing Dashboard UI...");
    uiOrchestrator.init();
    auth.setupLogoutButton();
  } else {
    // Fallback for logout functionality on other pages
    auth.setupLogoutButton();
  }

  console.log("Application initialization complete.");
});
