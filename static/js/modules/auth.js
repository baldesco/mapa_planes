/**
 * auth.js
 * Handles logic specific to the login and signup pages.
 */
import apiClient from "./apiClient.js"; // Use the centralized API client

// Helper function to delete a cookie by name client-side
function deleteCookie(name) {
  // Set expiry date to the past
  document.cookie = name + "=; Path=/; Expires=Thu, 01 Jan 1970 00:00:01 GMT;";
  console.debug(`Attempted to delete cookie '${name}' client-side.`);
}

const auth = {
  initLoginPage() {
    const loginForm = document.getElementById("login-form");
    const errorMessageDiv = document.getElementById("error-message");
    const infoMessageDiv = document.getElementById("info-message");

    if (!loginForm || !errorMessageDiv || !infoMessageDiv) {
      console.warn("Login page elements not found. Skipping login setup.");
      return;
    }

    console.debug("Initializing login page script...");

    // Check for query parameters on page load
    const urlParams = new URLSearchParams(window.location.search);
    const reason = urlParams.get("reason");
    const signupStatus = urlParams.get("signup");

    if (reason === "session_expired") {
      infoMessageDiv.textContent = "Your session expired. Please log in again.";
      infoMessageDiv.style.display = "block";
    } else if (reason === "logged_out") {
      infoMessageDiv.textContent = "You have been logged out successfully.";
      infoMessageDiv.style.display = "block";
    } else if (signupStatus === "success") {
      infoMessageDiv.textContent =
        "Signup successful! Please check your email for confirmation if needed, then log in.";
      infoMessageDiv.style.display = "block";
    }
    // Clear the query parameters from URL without reloading
    if (reason || signupStatus) {
      window.history.replaceState({}, document.title, window.location.pathname);
    }

    loginForm.addEventListener("submit", async (event) => {
      event.preventDefault();
      errorMessageDiv.style.display = "none";
      infoMessageDiv.style.display = "none";

      const formData = new FormData(loginForm);
      const submitButton = loginForm.querySelector('button[type="submit"]');
      if (submitButton) submitButton.disabled = true;

      try {
        const response = await apiClient.postForm(
          "/api/v1/auth/login",
          formData,
          {},
          true // Mark as login attempt
        );

        if (response.ok) {
          console.log("Login successful, redirecting...");
          window.location.href = "/"; // Redirect to root
        } else {
          let errorDetail = "Login failed. Please check your credentials.";
          try {
            const result = await response.json();
            errorDetail = result.detail || errorDetail;
          } catch (e) {
            /* ignore */
          }
          errorMessageDiv.textContent = errorDetail;
          errorMessageDiv.style.display = "block";
          if (submitButton) submitButton.disabled = false;
        }
      } catch (error) {
        console.error("Login error:", error);
        if (error.message.includes("Unauthorized")) {
          errorMessageDiv.textContent =
            "Login failed. Please check your credentials.";
        } else {
          errorMessageDiv.textContent =
            "An error occurred during login. Please try again.";
        }
        errorMessageDiv.style.display = "block";
        if (submitButton) submitButton.disabled = false;
      }
    });
  },

  initSignupPage() {
    const signupForm = document.getElementById("signup-form");
    const messageDiv = document.getElementById("message-div");

    if (!signupForm || !messageDiv) {
      console.warn("Signup page elements not found. Skipping signup setup.");
      return;
    }

    console.debug("Initializing signup page script...");

    signupForm.addEventListener("submit", async (event) => {
      event.preventDefault();
      messageDiv.style.display = "none";
      messageDiv.className = "message-auth";

      const email = document.getElementById("email").value;
      const password = document.getElementById("password").value;
      const submitButton = signupForm.querySelector('button[type="submit"]');
      if (submitButton) submitButton.disabled = true;

      try {
        const response = await apiClient.post("/api/v1/auth/signup", {
          email,
          password,
        });
        const result = await response.json();

        if (response.ok) {
          messageDiv.textContent =
            result.message || "Signup successful. Redirecting to login...";
          messageDiv.classList.add("success-message-auth");
          messageDiv.style.display = "block";
          setTimeout(() => {
            window.location.href = "/login?signup=success";
          }, 3000);
        } else {
          messageDiv.textContent =
            result.detail || "Signup failed. Please try again.";
          messageDiv.classList.add("error-message-auth");
          messageDiv.style.display = "block";
          if (submitButton) submitButton.disabled = false;
        }
      } catch (error) {
        console.error("Signup error:", error);
        messageDiv.textContent =
          "An error occurred during signup. Please try again.";
        messageDiv.classList.add("error-message-auth");
        messageDiv.style.display = "block";
        if (submitButton) submitButton.disabled = false;
      }
    });
  },

  setupLogoutButton() {
    const logoutButton = document.getElementById("logout-btn");
    if (!logoutButton) {
      return;
    }

    logoutButton.addEventListener("click", async () => {
      console.log("Logout button clicked");
      logoutButton.disabled = true; // Disable button during process

      try {
        const response = await apiClient.post("/api/v1/auth/logout", {});

        if (response.ok || response.status === 204) {
          console.log("Logout API call successful.");
          // --- Client-side cookie removal ---
          deleteCookie("access_token");
          // --- Redirect AFTER removing cookie ---
          window.location.href = "/login?reason=logged_out";
        } else {
          console.error(
            "Logout API call failed:",
            response.status,
            response.statusText
          );
          let errorDetail = "Logout failed. Please try again.";
          try {
            const errorData = await response.json();
            errorDetail = errorData.detail || errorDetail;
          } catch {
            /* ignore */
          }
          alert(`Logout failed: ${errorDetail}`);
          logoutButton.disabled = false; // Re-enable on failure
        }
      } catch (error) {
        console.error("Error during logout fetch:", error);
        // Handle potential network errors etc.
        if (!error.message.includes("Unauthorized")) {
          // Avoid double alert if apiClient already redirected
          alert("An error occurred during logout.");
        }
        // Even if API call failed, try deleting cookie and redirecting? Or just re-enable button?
        // Let's re-enable the button for now if API fails unexpectedly.
        logoutButton.disabled = false;
      }
    });
    console.debug("Logout button event listener attached.");
  },
};

export default auth;
