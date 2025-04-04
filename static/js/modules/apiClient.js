/**
 * apiClient.js
 * Module for handling fetch requests to the backend API.
 * Includes automatic redirection on 401 errors.
 */

const apiClient = {
  /**
   * Performs a fetch request with common configurations.
   * @param {string} url - The URL endpoint to fetch.
   * @param {object} options - Fetch options (method, headers, body, etc.).
   * @param {boolean} [isLoginAttempt=false] - Flag to prevent redirect loop on login failure.
   * @returns {Promise<Response>} - The fetch Response object.
   * @throws {Error} - Throws error on network failure or unexpected issues.
   */
  async fetch(url, options = {}, isLoginAttempt = false) {
    // Default headers can be set here if needed, e.g., Content-Type
    const defaultHeaders = {
      // Example: 'Content-Type': 'application/json', // Add if most requests are JSON
      // 'Accept': 'application/json', // Add if expecting JSON responses
      ...options.headers,
    };

    const fetchOptions = {
      ...options,
      headers: defaultHeaders,
      // credentials: 'include', // Usually needed if relying on cookies for auth state across origins
    };

    console.debug(`API Fetch: ${options.method || "GET"} ${url}`);

    try {
      const response = await fetch(url, fetchOptions);

      // Check for 401 Unauthorized and redirect if not a login attempt
      if (
        response.status === 401 &&
        !isLoginAttempt &&
        window.location.pathname !== "/login" // Avoid redirect if already on login page
      ) {
        console.warn(
          "Received 401 Unauthorized on API call, redirecting to login."
        );
        // Redirect with a reason parameter
        window.location.href = "/login?reason=session_expired";
        // Return a dummy response or throw an error to stop further processing
        // Throwing might be cleaner to signal failure immediately.
        throw new Error("Unauthorized - Session likely expired");
        // Or return a specific object: return { ok: false, status: 401, error: 'Unauthorized' };
      }

      // Log non-OK responses for debugging, but return the response for the caller to handle
      if (!response.ok) {
        console.warn(
          `API Response not OK: ${response.status} ${response.statusText} for ${url}`
        );
        // Attempt to parse error detail if available (caller should handle this ideally)
        // try {
        //     const errorData = await response.json();
        //     console.warn('Error Detail:', errorData.detail);
        // } catch (e) { /* Ignore if response is not JSON */ }
      }

      return response;
    } catch (error) {
      console.error(`API Fetch Error for ${url}:`, error);
      // Check for network errors
      if (error instanceof TypeError && error.message === "Failed to fetch") {
        console.error(
          "Network error: Could not connect to the server. Is the backend running?"
        );
        // Optionally display a user-friendly message here
      }
      // Re-throw the error so the calling function knows it failed
      throw error;
    }
  },

  // --- Specific API call helpers (Examples) ---

  /**
   * Performs a GET request.
   * @param {string} url - The URL endpoint.
   * @param {object} [options={}] - Additional fetch options.
   * @returns {Promise<Response>}
   */
  async get(url, options = {}) {
    return this.fetch(url, { ...options, method: "GET" });
  },

  /**
   * Performs a POST request, defaulting to JSON content type.
   * @param {string} url - The URL endpoint.
   * @param {object} body - The request body (will be JSON.stringify'd).
   * @param {object} [options={}] - Additional fetch options.
   * @returns {Promise<Response>}
   */
  async post(url, body, options = {}) {
    const defaultPostHeaders = {
      "Content-Type": "application/json",
      Accept: "application/json",
      ...options.headers,
    };
    return this.fetch(url, {
      ...options,
      method: "POST",
      headers: defaultPostHeaders,
      body: JSON.stringify(body),
    });
  },

  /**
   * Performs a POST request with FormData.
   * @param {string} url - The URL endpoint.
   * @param {FormData} formData - The FormData object.
   * @param {object} [options={}] - Additional fetch options.
   * @returns {Promise<Response>}
   */
  async postForm(url, formData, options = {}) {
    // When using FormData, browser sets Content-Type automatically with boundary
    return this.fetch(url, {
      ...options,
      method: "POST",
      body: formData,
      // Do NOT set Content-Type header here
    });
  },

  /**
   * Performs a PUT request, defaulting to JSON content type.
   * @param {string} url - The URL endpoint.
   * @param {object} body - The request body (will be JSON.stringify'd).
   * @param {object} [options={}] - Additional fetch options.
   * @returns {Promise<Response>}
   */
  async put(url, body, options = {}) {
    const defaultPutHeaders = {
      "Content-Type": "application/json",
      Accept: "application/json",
      ...options.headers,
    };
    return this.fetch(url, {
      ...options,
      method: "PUT",
      headers: defaultPutHeaders,
      body: JSON.stringify(body),
    });
  },

  /**
   * Performs a DELETE request.
   * @param {string} url - The URL endpoint.
   * @param {object} [options={}] - Additional fetch options.
   * @returns {Promise<Response>}
   */
  async delete(url, options = {}) {
    return this.fetch(url, { ...options, method: "DELETE" });
  },
};

export default apiClient;
