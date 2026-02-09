/**
 * passwordReset.js
 * Handles logic for requesting reset links and updating passwords.
 * Standardized to use the centralized apiClient and global Supabase instance.
 */
import apiClient from "./apiClient.js";

const passwordReset = {
  /**
   * Initializes the request reset link page.
   */
  initRequestPage() {
    const form = document.getElementById("request-reset-form");
    const messageDiv = document.getElementById("message-div");

    if (!form) return;

    form.addEventListener("submit", async (e) => {
      e.preventDefault();
      const email = document.getElementById("email").value;
      const submitBtn = form.querySelector('button[type="submit"]');

      submitBtn.disabled = true;
      if (messageDiv) {
        messageDiv.style.display = "none";
        messageDiv.className = "message-auth";
      }

      try {
        const response = await apiClient.post(
          "/api/v1/auth/request-password-reset",
          { email },
        );
        const result = await apiClient.parseResponse(response);

        if (messageDiv) {
          messageDiv.textContent =
            result.message ||
            "If an account exists, a reset link has been sent.";
          messageDiv.className = "message-auth success-message-auth";
          messageDiv.style.display = "block";
        }
      } catch (err) {
        if (messageDiv) {
          messageDiv.textContent = "An error occurred. Please try again.";
          messageDiv.className = "message-auth error-message-auth";
          messageDiv.style.display = "block";
        }
        submitBtn.disabled = false;
      }
    });
  },

  /**
   * Initializes the final password reset page using the Supabase JS client.
   */
  initResetPage() {
    const form = document.getElementById("reset-password-form");
    const messageDiv = document.getElementById("message-div");

    // Check for the global Supabase client instance required for the secure update
    const supabase = window.supabaseClientInstance;

    if (!form || !supabase) {
      if (messageDiv) {
        messageDiv.textContent =
          "Reset service configuration error. Please refresh.";
        messageDiv.className = "message-auth error-message-auth";
        messageDiv.style.display = "block";
      }
      if (form) form.style.display = "none";
      return;
    }

    form.addEventListener("submit", async (e) => {
      e.preventDefault();
      const newPassword = document.getElementById("new_password").value;
      const confirmPassword = document.getElementById("confirm_password").value;
      const submitBtn = form.querySelector('button[type="submit"]');

      if (newPassword !== confirmPassword) {
        this.showMessage(messageDiv, "Passwords do not match.", "error");
        return;
      }

      if (newPassword.length < 8) {
        this.showMessage(
          messageDiv,
          "Password must be at least 8 characters.",
          "error",
        );
        return;
      }

      submitBtn.disabled = true;
      this.showMessage(messageDiv, "Updating password...", "info");

      try {
        const { error } = await supabase.auth.updateUser({
          password: newPassword,
        });

        if (error) {
          this.showMessage(messageDiv, `Error: ${error.message}`, "error");
          submitBtn.disabled = false;
        } else {
          this.showMessage(
            messageDiv,
            "Success! Redirecting to login...",
            "success",
          );
          setTimeout(() => {
            window.location.href = "/login?reason=password_reset_success";
          }, 2500);
        }
      } catch (err) {
        this.showMessage(messageDiv, "An unexpected error occurred.", "error");
        submitBtn.disabled = false;
      }
    });
  },

  showMessage(el, text, type) {
    if (!el) return;
    el.textContent = text;
    el.className = `message-auth ${type}-message-auth`;
    el.style.display = "block";
  },
};

export default passwordReset;
