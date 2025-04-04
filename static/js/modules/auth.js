/**
 * auth.js
 * Handles logic specific to the login and signup pages.
 */
import apiClient from "./apiClient.js"; // Use the centralized API client

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
        // Use apiClient.postForm for FormData, mark as login attempt
        const response = await apiClient.postForm(
          "/api/v1/auth/login",
          formData,
          {},
          true // Mark as login attempt
        );

        if (response.ok) {
          // Login successful, token is set in HttpOnly cookie by backend.
          // Redirect to the main map page.
          console.log("Login successful, redirecting...");
          window.location.href = "/"; // Redirect to root
        } else {
          // Display error message from API response
          let errorDetail = "Login failed. Please check your credentials.";
          try {
            const result = await response.json();
            errorDetail = result.detail || errorDetail;
          } catch (e) {
            /* ignore if response not json */
          }
          errorMessageDiv.textContent = errorDetail;
          errorMessageDiv.style.display = "block";
          if (submitButton) submitButton.disabled = false; // Re-enable button on failure
        }
      } catch (error) {
        console.error("Login error:", error);
        // Handle specific errors like network errors if needed
        if (error.message.includes("Unauthorized")) {
          // This case shouldn't happen if isLoginAttempt=true, but as fallback:
          errorMessageDiv.textContent =
            "Login failed. Please check your credentials.";
        } else {
          errorMessageDiv.textContent =
            "An error occurred during login. Please try again.";
        }
        errorMessageDiv.style.display = "block";
        if (submitButton) submitButton.disabled = false; // Re-enable button on error
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
      messageDiv.className = "message-auth"; // Reset classes

      const email = document.getElementById("email").value;
      const password = document.getElementById("password").value;
      const submitButton = signupForm.querySelector('button[type="submit"]');
      if (submitButton) submitButton.disabled = true;

      // Basic password confirmation check (optional)
      // const passwordConfirm = document.getElementById('password-confirm')?.value;
      // if (passwordConfirm && password !== passwordConfirm) {
      //     messageDiv.textContent = 'Passwords do not match.';
      //     messageDiv.classList.add('error-message-auth');
      //     messageDiv.style.display = 'block';
      //     if (submitButton) submitButton.disabled = false;
      //     return;
      // }

      try {
        // Use apiClient.post for JSON data
        const response = await apiClient.post("/api/v1/auth/signup", {
          email: email,
          password: password,
        });

        const result = await response.json(); // Assume backend always returns JSON

        if (response.ok) {
          messageDiv.textContent =
            result.message || "Signup successful. Redirecting to login...";
          messageDiv.classList.add("success-message-auth");
          messageDiv.style.display = "block";
          // Redirect to login after a short delay
          setTimeout(() => {
            window.location.href = "/login?signup=success";
          }, 3000); // 3 seconds delay
        } else {
          messageDiv.textContent =
            result.detail || "Signup failed. Please try again.";
          messageDiv.classList.add("error-message-auth");
          messageDiv.style.display = "block";
          if (submitButton) submitButton.disabled = false; // Re-enable on failure
        }
      } catch (error) {
        console.error("Signup error:", error);
        messageDiv.textContent =
          "An error occurred during signup. Please try again.";
        messageDiv.classList.add("error-message-auth");
        messageDiv.style.display = "block";
        if (submitButton) submitButton.disabled = false; // Re-enable on error
      }
    });
  },

  setupLogoutButton() {
    const logoutButton = document.getElementById("logout-btn");
    if (!logoutButton) {
      // This might be expected if the button isn't on every page
      // console.debug("#logout-btn not found on this page.");
      return;
    }

    logoutButton.addEventListener("click", async () => {
      console.log("Logout button clicked");
      try {
        // Use apiClient.post (no body needed for logout)
        const response = await apiClient.post("/api/v1/auth/logout", {});

        // Logout should return 204 No Content on success
        if (response.ok || response.status === 204) {
          console.log("Logout API call successful.");
          window.location.href = "/login?reason=logged_out"; // Force redirect
        } else {
          console.error(
            "Logout API call failed:",
            response.status,
            response.statusText
          );
          let errorDetail = "Logout failed. Please try again.";
          try {
            // Attempt to get error detail if backend sends one
            const errorData = await response.json();
            errorDetail = errorData.detail || errorDetail;
          } catch {
            /* ignore if response not json */
          }
          alert(`Logout failed: ${errorDetail}`);
        }
      } catch (error) {
        // Handle errors thrown by apiClient (e.g., network error, 401 redirect)
        console.error("Error during logout fetch:", error);
        if (!error.message.includes("Unauthorized")) {
          // Avoid alerting if it was just the 401 redirect
          alert("An error occurred during logout.");
        }
      }
    });
    console.debug("Logout button event listener attached.");
  },
};

export default auth;
