/**
 * auth.js
 * Handles authentication logic for login, signup, and logout.
 * Updated to use centralized apiClient and SPA-lite redirection.
 */
import apiClient from "./apiClient.js";

const auth = {
  /**
   * Initializes the login page logic.
   */
  initLoginPage() {
    const loginForm = document.getElementById("login-form");
    const errorDiv = document.getElementById("error-message");
    const infoDiv = document.getElementById("info-message");

    if (!loginForm) return;

    loginForm.addEventListener("submit", async (e) => {
      e.preventDefault();
      if (errorDiv) errorDiv.style.display = "none";

      const formData = new FormData(loginForm);
      const submitBtn = loginForm.querySelector('button[type="submit"]');
      if (submitBtn) submitBtn.disabled = true;

      try {
        // PostForm is used because the endpoint expects OAuth2 form data
        const response = await apiClient.postForm(
          "/api/v1/auth/login",
          formData,
          {},
          true,
        );

        if (response.ok) {
          window.location.href = "/";
        } else {
          const result = await apiClient.parseResponse(response);
          if (errorDiv) {
            errorDiv.textContent =
              result.detail || "Invalid email or password.";
            errorDiv.style.display = "block";
          }
          if (submitBtn) submitBtn.disabled = false;
        }
      } catch (err) {
        if (submitBtn) submitBtn.disabled = false;
      }
    });
  },

  /**
   * Initializes the signup page logic.
   */
  initSignupPage() {
    const signupForm = document.getElementById("signup-form");
    const messageDiv = document.getElementById("message-div");

    if (!signupForm) return;

    signupForm.addEventListener("submit", async (e) => {
      e.preventDefault();
      const email = document.getElementById("email").value;
      const password = document.getElementById("password").value;
      const submitBtn = signupForm.querySelector('button[type="submit"]');

      if (submitBtn) submitBtn.disabled = true;

      try {
        const response = await apiClient.post("/api/v1/auth/signup", {
          email,
          password,
        });
        const result = await apiClient.parseResponse(response);

        if (response.ok) {
          if (messageDiv) {
            messageDiv.textContent =
              "Signup successful! Redirecting to login...";
            messageDiv.className = "message-auth success-message-auth";
            messageDiv.style.display = "block";
          }
          setTimeout(
            () => (window.location.href = "/login?signup=success"),
            2000,
          );
        } else {
          if (messageDiv) {
            messageDiv.textContent = result.detail || "Signup failed.";
            messageDiv.className = "message-auth error-message-auth";
            messageDiv.style.display = "block";
          }
          if (submitBtn) submitBtn.disabled = false;
        }
      } catch (err) {
        if (submitBtn) submitBtn.disabled = false;
      }
    });
  },

  /**
   * Configures the global logout button functionality.
   */
  setupLogoutButton() {
    const logoutBtn = document.getElementById("logout-btn");
    if (!logoutBtn) return;

    logoutBtn.addEventListener("click", async () => {
      logoutBtn.disabled = true;
      try {
        const response = await apiClient.post("/api/v1/auth/logout", {});

        // Clear cookie client-side as well for extra safety
        document.cookie =
          "access_token=; Path=/; Expires=Thu, 01 Jan 1970 00:00:01 GMT;";

        window.location.href = "/login?reason=logged_out";
      } catch (err) {
        console.error("Logout failed:", err);
        logoutBtn.disabled = false;
      }
    });
  },
};

export default auth;
