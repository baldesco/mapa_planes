/**
 * apiClient.js
 * Centralized fetch wrapper for backend API communication.
 * Handles authentication redirects and standardized error parsing.
 */

const apiClient = {
  /**
   * Core fetch wrapper with standard configuration and error handling.
   */
  async fetch(url, options = {}, isLoginAttempt = false) {
    const defaultHeaders = {
      ...options.headers,
    };

    const fetchOptions = {
      ...options,
      headers: defaultHeaders,
    };

    try {
      const response = await fetch(url, fetchOptions);

      // Handle session expiration or unauthorized access
      if (response.status === 401 && !isLoginAttempt) {
        if (window.location.pathname !== "/login") {
          window.location.href = "/login?reason=session_expired";
        }
        throw new Error("Unauthorized access - redirecting to login.");
      }

      return response;
    } catch (error) {
      console.error(`API Client Error [${url}]:`, error);
      throw error;
    }
  },

  /**
   * GET request helper.
   */
  async get(url, options = {}) {
    return this.fetch(url, { ...options, method: "GET" });
  },

  /**
   * POST request helper (defaults to JSON).
   */
  async post(url, body, options = {}) {
    return this.fetch(url, {
      ...options,
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        ...options.headers,
      },
      body: JSON.stringify(body),
    });
  },

  /**
   * POST request helper for FormData (browser sets boundary automatically).
   */
  async postForm(url, formData, options = {}) {
    return this.fetch(url, {
      ...options,
      method: "POST",
      body: formData,
    });
  },

  /**
   * PUT request helper (defaults to JSON).
   */
  async put(url, body, options = {}) {
    return this.fetch(url, {
      ...options,
      method: "PUT",
      headers: {
        "Content-Type": "application/json",
        ...options.headers,
      },
      body: JSON.stringify(body),
    });
  },

  /**
   * DELETE request helper.
   */
  async delete(url, options = {}) {
    return this.fetch(url, { ...options, method: "DELETE" });
  },

  /**
   * Utility to safely parse JSON from a response object.
   */
  async parseResponse(response) {
    try {
      return await response.json();
    } catch (e) {
      return { detail: "Unexpected server response format." };
    }
  },
};

export default apiClient;
