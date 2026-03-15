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
    const defaultHeaders = {
      ...options.headers,
    };

    const fetchOptions = {
      ...options,
      headers: defaultHeaders,
    };

    console.debug(`API Fetch: ${options.method || "GET"} ${url}`);

    const loader = document.getElementById("global-loader");
    const loaderStartTime = Date.now();
    
    if (loader && !url.includes("search")) {
        loader.classList.add("active");
    }

    try {
      const response = await fetch(url, fetchOptions);

      if (
        response.status === 401 &&
        !isLoginAttempt &&
        window.location.pathname !== "/login"
      ) {
        console.warn(
          "Received 401 Unauthorized on API call, redirecting to login."
        );
        window.location.href = "/login?reason=session_expired";
        throw new Error("Unauthorized - Session likely expired");
      }

      if (!response.ok) {
        console.warn(
          `API Response not OK: ${response.status} ${response.statusText} for ${url}`
        );
      }

      return response;
    } catch (error) {
      console.error(`API Fetch Error for ${url}:`, error);
      if (error instanceof TypeError && error.message === "Failed to fetch") {
        console.error(
          "Network error: Could not connect to the server. Is the backend running?"
        );
      }
      throw error;
    } finally {
      if (loader) {
          // Enforce a minimum display time of 400ms so it doesn't just flash invisibly on fast local networks
          const elapsedTime = Date.now() - loaderStartTime;
          const minDisplayTime = 400; 
          
          if (elapsedTime < minDisplayTime) {
              setTimeout(() => {
                  loader.classList.remove("active");
              }, minDisplayTime - elapsedTime);
          } else {
              loader.classList.remove("active");
          }
      }
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

  /**
   * Performs a PATCH request, defaulting to JSON content type.
   * @param {string} url - The URL endpoint.
   * @param {object} [body] - The request body.
   * @param {object} [options={}] - Additional fetch options.
   * @returns {Promise<Response>}
   */
  async patch(url, body, options = {}) {
    const defaultHeaders = {
      "Content-Type": "application/json",
      Accept: "application/json",
      ...options.headers,
    };
    const fetchOptions = {
      ...options,
      method: "PATCH",
      headers: defaultHeaders,
    };
    if (body) fetchOptions.body = JSON.stringify(body);
    return this.fetch(url, fetchOptions);
  },

  /**
   * Performs a PATCH request with FormData.
   * @param {string} url - The URL endpoint.
   * @param {FormData} formData - The FormData object.
   * @param {object} [options={}] - Additional fetch options.
   * @returns {Promise<Response>}
   */
  async patchForm(url, formData, options = {}) {
    return this.fetch(url, {
      ...options,
      method: "PATCH",
      body: formData,
    });
  },
};

export default apiClient;
