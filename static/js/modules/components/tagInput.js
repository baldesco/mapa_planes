/**
 * tagInput.js
 * Component module for initializing and managing Tagify instances.
 * Optimized for SPA-lite lifecycle management and filtering.
 */

const tagInput = {
  tagifyInstances: {},

  /**
   * Initializes Tagify on a given input element.
   */
  init(inputElementId, whitelist = [], options = {}) {
    const inputEl = document.getElementById(inputElementId);
    if (!inputEl) return null;

    // Clean up existing instance if any
    this.destroy(inputElementId);

    const defaultSettings = {
      whitelist: whitelist || [],
      maxTags: 15,
      dropdown: {
        maxItems: 20,
        enabled: 0,
        closeOnSelect: true,
      },
      // Consistent format for backend CSV parsing
      originalInputValueFormat: (valuesArr) =>
        valuesArr.map((item) => item.value).join(","),
      ...options,
    };

    try {
      const instance = new Tagify(inputEl, defaultSettings);
      this.tagifyInstances[inputElementId] = instance;
      return instance;
    } catch (e) {
      console.error(`Tagify error on #${inputElementId}:`, e);
      return null;
    }
  },

  /**
   * Sets tags for an existing instance.
   */
  setTags(inputElementId, tags = []) {
    const instance = this.tagifyInstances[inputElementId];
    if (instance) {
      instance.removeAllTags();
      instance.addTags(tags);
    }
  },

  /**
   * Retrieves an array of tag values.
   */
  getTags(inputElementId) {
    const instance = this.tagifyInstances[inputElementId];
    if (instance) {
      return instance.value.map((t) => t.value);
    }

    // Fallback to manual parsing if instance is missing
    const el = document.getElementById(inputElementId);
    return el
      ? el.value
          .split(",")
          .filter(Boolean)
          .map((t) => t.trim())
      : [];
  },

  /**
   * Properly destroys an instance and removes it from the local registry.
   */
  destroy(inputElementId) {
    const instance = this.tagifyInstances[inputElementId];
    if (instance) {
      try {
        instance.destroy();
        delete this.tagifyInstances[inputElementId];
      } catch (e) {
        console.warn(`Error destroying Tagify on #${inputElementId}:`, e);
      }
    }
  },

  /**
   * Global cleanup for all instances (e.g., on logout or major navigation).
   */
  destroyAll() {
    Object.keys(this.tagifyInstances).forEach((id) => this.destroy(id));
  },
};

export default tagInput;
