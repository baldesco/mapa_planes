/**
 * statusMessages.js
 * Utility function for displaying status messages in designated elements.
 */

/**
 * Sets the text content and CSS class for a status message element.
 * @param {HTMLElement|null} element - The DOM element to display the message in.
 * @param {string} message - The message text. Clears message if empty.
 * @param {'info'|'success'|'error'|'loading'} [type='info'] - The type of message for styling.
 */
function setStatusMessage(element, message, type = "info") {
  if (!element) {
    // console.warn("setStatusMessage: Target element is null or undefined.");
    return; // Do nothing if element doesn't exist
  }

  element.textContent = message;
  // Reset classes first, keep base class
  element.className = "status-message";

  // Add type-specific class
  if (type === "error") {
    element.classList.add("error-message");
  } else if (type === "success") {
    element.classList.add("success-message");
  } else if (type === "loading") {
    element.classList.add("loading-indicator");
  } else {
    // Default to 'info'
    element.classList.add("info-message");
  }

  // Show or hide based on message content
  element.style.display = message ? "block" : "none";
}

// Export the function directly if it's the only thing in the module
export { setStatusMessage };

// Alternatively, export as part of an object:
// const statusMessages = { setStatusMessage };
// export default statusMessages;
