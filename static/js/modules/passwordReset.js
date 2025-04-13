/**
 * passwordReset.js
 * Handles logic for the password reset request and confirmation pages.
 */
import apiClient from "./apiClient.js";

const passwordReset = {
  // No need to store token globally anymore

  initRequestPage() {
    const requestForm = document.getElementById("request-reset-form");
    const messageDiv = document.getElementById("message-div");

    if (!requestForm || !messageDiv) {
      console.warn(
        "Request password reset page elements not found. Skipping setup."
      );
      return;
    }

    requestForm.addEventListener("submit", async (event) => {
      event.preventDefault();
      messageDiv.style.display = "none";
      messageDiv.className = "message-auth"; // Reset class

      const email = document.getElementById("email").value;
      const submitButton = requestForm.querySelector('button[type="submit"]');
      if (submitButton) submitButton.disabled = true;

      try {
        const apiUrl = "/api/v1/auth/request-password-reset";
        const response = await apiClient.post(apiUrl, { email });
        const result = await response.json();

        // Always show a generic success message for security
        messageDiv.textContent =
          result.message ||
          "Password reset instructions sent (if account exists).";
        messageDiv.classList.add("success-message-auth");
        if (!response.ok) {
          console.error("Password reset request failed:", result.detail);
        }
      } catch (error) {
        console.error("Error requesting password reset:", error);
        // Still show generic message on unexpected error
        messageDiv.textContent =
          "Password reset instructions sent (if account exists).";
        messageDiv.classList.add("success-message-auth");
      } finally {
        messageDiv.style.display = "block";
        // Keep button disabled after submission to prevent spamming
      }
    });
  },

  initResetPage() {
    const resetForm = document.getElementById("reset-password-form");
    const messageDiv = document.getElementById("message-div");
    const tokenInput = document.getElementById("recovery_token");
    const typeInput = document.getElementById("recovery_type");

    if (!resetForm || !messageDiv || !tokenInput || !typeInput) {
      console.warn("Reset password page elements not found. Skipping setup.");
      return;
    }

    // --- Extract Token and Type from URL Fragment ---
    const hash = window.location.hash.substring(1); // Remove '#'
    const params = new URLSearchParams(hash);
    const accessToken = params.get("access_token");
    const recoveryType = params.get("type"); // Usually 'recovery'

    if (!accessToken || !recoveryType) {
      console.error(
        "Reset password page: Access token or type not found in URL hash."
      );
      messageDiv.textContent =
        "Error: Invalid or missing password reset link parameters. Please request a new one.";
      messageDiv.className = "message-auth error-message-auth";
      messageDiv.style.display = "block";
      resetForm.style.display = "none"; // Hide form if params missing
      return; // Stop initialization
    } else {
      // Populate hidden form fields
      tokenInput.value = accessToken;
      typeInput.value = recoveryType;

      // Clear the token from the URL bar for security
      window.history.replaceState(
        {},
        document.title,
        window.location.pathname + window.location.search
      );
      console.debug("Token and type extracted and cleared from URL hash.");
    }
    // --- End Token Extraction ---

    resetForm.addEventListener("submit", async (event) => {
      event.preventDefault();
      messageDiv.style.display = "none";
      messageDiv.className = "message-auth";

      const newPassword = document.getElementById("new_password").value;
      const confirmPassword = document.getElementById("confirm_password").value;
      const submitButton = resetForm.querySelector('button[type="submit"]');

      if (newPassword !== confirmPassword) {
        messageDiv.textContent = "Passwords do not match.";
        messageDiv.classList.add("error-message-auth");
        messageDiv.style.display = "block";
        return;
      }

      if (newPassword.length < 8) {
        messageDiv.textContent = "Password must be at least 8 characters long.";
        messageDiv.classList.add("error-message-auth");
        messageDiv.style.display = "block";
        return;
      }

      if (submitButton) submitButton.disabled = true;

      // Create FormData from the form
      const formData = new FormData(resetForm);

      // *** FIX: Remove the confirm_password field before sending ***
      formData.delete("confirm_password");
      console.debug("Removed confirm_password from FormData before sending.");

      // *** DEBUG: Log FormData keys after deletion ***
      console.debug("FormData keys being sent:", [...formData.keys()]);
      // *** END DEBUG ***

      try {
        const apiUrl = "/api/v1/auth/reset-password";
        // Use postForm, no explicit Authorization header needed now
        const response = await apiClient.postForm(apiUrl, formData);

        const result = await response.json();

        if (response.ok) {
          messageDiv.textContent =
            result.message || "Password updated successfully! Redirecting...";
          messageDiv.classList.add("success-message-auth");
          messageDiv.style.display = "block";
          setTimeout(() => {
            window.location.href = "/login?reason=password_reset_success";
          }, 3000);
        } else {
          messageDiv.textContent =
            result.detail ||
            "Failed to update password. The link may have expired, the password doesn't meet requirements, or the token was invalid.";
          messageDiv.classList.add("error-message-auth");
          messageDiv.style.display = "block";
          if (submitButton) submitButton.disabled = false;
        }
      } catch (error) {
        console.error("Error resetting password:", error);
        messageDiv.textContent =
          "An error occurred while updating your password. Please try again or request a new reset link.";
        messageDiv.classList.add("error-message-auth");
        messageDiv.style.display = "block";
        if (submitButton) submitButton.disabled = false;
      }
    });
  },
};

export default passwordReset;
