/**
 * statusMessages.js
 * Utility function for displaying standardized status messages.
 * Integrated with the SPA-lite CSS system.
 */

/**
 * Sets the text content and CSS class for a status message element.
 * @param {HTMLElement|null} element - The DOM element to display the message in.
 * @param {string} message - The message text. Clears message if empty.
 * @param {'info'|'success'|'error'|'loading'} [type='info'] - The type of message for styling.
 */
export function setStatusMessage(element, message, type = "info") {
  if (!element) return;

  element.textContent = message;

  // Base class for layout, specific classes for colors/icons
  element.className = "status-message";

  if (type === "error") {
    element.classList.add("error-message");
  } else if (type === "success") {
    element.classList.add("success-message");
  } else if (type === "loading") {
    element.classList.add("loading-indicator");
  } else {
    element.classList.add("info-message");
  }

  // Show/Hide logic
  element.style.display = message ? "block" : "none";
}
