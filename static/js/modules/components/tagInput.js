/**
 * tagInput.js
 * Component module for initializing and managing Tagify instances.
 */

const tagInput = {
  tagifyInstances: {}, // Store instances by input element ID

  /**
   * Initializes Tagify on a given input element.
   * @param {string} inputElementId - The ID of the input element.
   * @param {Array<string>} whitelist - An array of predefined tag names for suggestions.
   * @param {object} [options={}] - Optional Tagify configuration overrides.
   * @returns {Tagify|null} The initialized Tagify instance or null on error.
   */
  init(inputElementId, whitelist = [], options = {}) {
    const inputEl = document.getElementById(inputElementId);
    if (!inputEl) {
      console.error(
        `Tagify init failed: Element #${inputElementId} not found.`
      );
      return null;
    }

    // Destroy previous instance if exists for this element
    if (this.tagifyInstances[inputElementId]) {
      try {
        this.tagifyInstances[inputElementId].destroy();
        console.debug(
          `Destroyed previous Tagify instance for #${inputElementId}`
        );
      } catch (e) {
        console.warn(
          `Error destroying previous Tagify instance for #${inputElementId}:`,
          e
        );
      }
    }

    // Default Tagify settings
    const defaultSettings = {
      whitelist: whitelist || [], // Initial suggestions list
      maxTags: 10, // Limit number of tags
      dropdown: {
        maxItems: 20, // Max suggestions shown
        classname: "tags-look", // Custom class for dropdown styling
        enabled: 0, // Show suggestions on focus/input (0 means always)
        closeOnSelect: false, // Keep dropdown open after selection
      },
      // Allow adding tags not in the whitelist (new tags)
      // enforceWhitelist: false, // Set to true if ONLY existing tags allowed
      editTags: false, // Disable editing tags directly by double-clicking
      // You might want `delimiters` if pasting comma-separated tags: delimiters: ",| ",
      originalInputValueFormat: (valuesArr) =>
        valuesArr.map((item) => item.value).join(","), // How value is stored in original input
      ...options, // Allow overriding defaults
    };

    try {
      const tagifyInstance = new Tagify(inputEl, defaultSettings);
      this.tagifyInstances[inputElementId] = tagifyInstance;
      console.log(`Tagify initialized for #${inputElementId}`);

      // Optional: Add event listeners if needed
      // tagifyInstance.on('add', event => console.log('Tag added:', event.detail));
      // tagifyInstance.on('remove', event => console.log('Tag removed:', event.detail));
      // tagifyInstance.on('input', event => console.log('Tag input:', event.detail)); // Good for dynamic suggestions fetch

      return tagifyInstance;
    } catch (e) {
      console.error(`Error initializing Tagify for #${inputElementId}:`, e);
      return null;
    }
  },

  /**
   * Sets the tags for a specific Tagify instance.
   * @param {string} inputElementId - The ID of the input element associated with the Tagify instance.
   * @param {Array<string>} tags - An array of tag names to set.
   */
  setTags(inputElementId, tags = []) {
    const tagify = this.tagifyInstances[inputElementId];
    if (tagify) {
      try {
        tagify.removeAllTags(); // Clear existing tags first
        tagify.addTags(tags); // Add the new tags
        console.debug(`Set tags for #${inputElementId}:`, tags);
      } catch (e) {
        console.error(
          `Error setting tags for Tagify instance #${inputElementId}:`,
          e
        );
      }
    } else {
      console.warn(
        `Cannot set tags: Tagify instance for #${inputElementId} not found.`
      );
    }
  },

  /**
   * Gets the current tags from a specific Tagify instance.
   * @param {string} inputElementId - The ID of the input element associated with the Tagify instance.
   * @returns {Array<string>} An array of the current tag names, or empty array if not found/error.
   */
  getTags(inputElementId) {
    const tagify = this.tagifyInstances[inputElementId];
    if (tagify) {
      try {
        // Get tag data objects and extract the 'value' (the tag name)
        return tagify.value.map((tagData) => tagData.value);
      } catch (e) {
        console.error(
          `Error getting tags from Tagify instance #${inputElementId}:`,
          e
        );
        return [];
      }
    } else {
      console.warn(
        `Cannot get tags: Tagify instance for #${inputElementId} not found.`
      );
      // Fallback: try reading the original input's value directly? Might be unreliable.
      const inputEl = document.getElementById(inputElementId);
      if (inputEl && inputEl.value) {
        return inputEl.value
          .split(",")
          .map((t) => t.trim())
          .filter((t) => t);
      }
      return [];
    }
  },

  /**
   * Destroys a specific Tagify instance and removes it from storage.
   * @param {string} inputElementId - The ID of the input element.
   */
  destroy(inputElementId) {
    const tagify = this.tagifyInstances[inputElementId];
    if (tagify) {
      try {
        tagify.destroy();
        delete this.tagifyInstances[inputElementId];
        console.log(`Tagify instance destroyed for #${inputElementId}`);
      } catch (e) {
        console.error(
          `Error destroying Tagify instance #${inputElementId}:`,
          e
        );
      }
    }
  },
};

export default tagInput;
