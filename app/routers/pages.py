/**
 * passwordReset.js
 * Handles logic for the password reset request and confirmation pages.
 * Uses Supabase JS client for the update on the reset page.
 */

const passwordReset = {
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
        // Dynamically import apiClient only when needed
        const apiClient = (await import("./apiClient.js")).default;
        const apiUrl = "/api/v1/auth/request-password-reset";
        const response = await apiClient.post(apiUrl, { email });
        const result = await response.json();

        messageDiv.textContent =
          result.message ||
          "Password reset instructions sent (if account exists).";
        messageDiv.classList.add("success-message-auth");
        if (!response.ok) {
          console.error("Password reset request failed:", result.detail);
        }
      } catch (error) {
        console.error("Error requesting password reset:", error);
        messageDiv.textContent =
          "Password reset instructions sent (if account exists).";
        messageDiv.classList.add("success-message-auth");
      } finally {
        messageDiv.style.display = "block";
        // Keep button disabled
      }
    });
  },

  initResetPage() {
    const resetForm = document.getElementById("reset-password-form");
    const messageDiv = document.getElementById("message-div");

    if (!resetForm || !messageDiv) {
      console.warn("Reset password page elements not found. Skipping setup.");
      return;
    }

    // Check if Supabase client INSTANCE was initialized and made available globally
    if (typeof window.supabaseClientInstance === 'undefined' || !window.supabaseClientInstance) {
        messageDiv.textContent = "Password reset service is unavailable due to a configuration error.";
        messageDiv.className = "message-auth error-message-auth";
        messageDiv.style.display = "block";
        console.error("Supabase JS client instance ('supabaseClientInstance' global) not available.");
        resetForm.style.display = 'none'; // Hide form if client not ready
        return;
    }
    // Use the initialized client instance
    const supabase = window.supabaseClientInstance;

    resetForm.addEventListener("submit", async (event) => {
        event.preventDefault(); // Prevent default HTML submission
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
        messageDiv.textContent = "Updating password...";
        messageDiv.className = "message-auth info-message-auth";
        messageDiv.style.display = 'block';

        try {
            // Call Supabase JS updateUser method
            console.debug("Calling supabase.auth.updateUser with new password...");
            const { data, error } = await supabase.auth.updateUser({
                password: newPassword
            });

            if (error) {
                console.error("Supabase JS updateUser error:", error);
                let detail = error.message || "Failed to update password.";
                if (error.message.includes("Password") && error.message.includes("requirement")) {
                    detail = "Password does not meet requirements.";
                } else if (error.message.includes("session") || error.message.includes("token")) {
                    detail = "Password reset session invalid or expired. Please request a new reset link.";
                }
                messageDiv.textContent = `Error: ${detail}`;
                messageDiv.className = "message-auth error-message-auth";
                messageDiv.style.display = "block";
                if (submitButton) submitButton.disabled = false; // Re-enable on error
            } else {
                 // Password updated successfully
                 console.log("Supabase JS updateUser success:", data);
                 messageDiv.textContent = "Password updated successfully! Redirecting...";
                 messageDiv.className = "message-auth success-message-auth";
                 messageDiv.style.display = "block";
                 submitButton.disabled = true; // Keep disabled on success
                 document.getElementById("new_password").value = '';
                 document.getElementById("confirm_password").value = '';

                 setTimeout(() => {
                    window.location.href = "/login?reason=password_reset_success";
                 }, 3000);
            }
        } catch (error) { // Catch unexpected JS errors
            console.error("Unexpected error during password update:", error);
            messageDiv.textContent = "An unexpected error occurred. Please try again.";
            messageDiv.className = "message-auth error-message-auth";
            messageDiv.style.display = "block";
            if (submitButton) submitButton.disabled = false;
        }
    });
    console.debug("Reset password page initialized using Supabase JS client.");
  },
};

export default passwordReset;