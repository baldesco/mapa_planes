document.addEventListener("DOMContentLoaded", function () {
  // --- Global Variables & State ---
  let leafletMap = null; // Explicitly store Leaflet map instance
  let mapClickHandler = null;
  let isPinningMode = false;
  let temporaryMarker = null;

  // --- DOM Elements ---
  // (Keep all existing DOM element variables)
  const toggleAddPlaceBtn = document.getElementById(
    "toggle-add-place-form-btn"
  );
  const addPlaceWrapper = document.getElementById("add-place-wrapper-section");
  const addPlaceForm = document.getElementById("add-place-form");
  const addPlaceCancelBtn = document.getElementById("add-place-cancel-btn");
  const addressInput = document.getElementById("address-input");
  const findCoordsBtn = document.getElementById("find-coords-btn");
  const geocodeStatus = document.getElementById("geocode-status");
  const coordsSection = document.getElementById("coords-section");
  const displayLat = document.getElementById("display-lat");
  const displayLon = document.getElementById("display-lon");
  const displayAddress = document.getElementById("display-address");
  const hiddenLat = document.getElementById("latitude");
  const hiddenLon = document.getElementById("longitude");
  const hiddenAddress = document.getElementById("address");
  const hiddenCity = document.getElementById("city");
  const hiddenCountry = document.getElementById("country");
  const addSubmitBtn = document.getElementById("add-place-submit-btn");
  const nameInput = document.getElementById("name");
  const addCategorySelect = document.getElementById("add-category");
  const addStatusSelect = document.getElementById("add-status");
  const pinOnMapBtn = document.getElementById("pin-on-map-btn");
  const mapPinInstruction = document.getElementById("map-pin-instruction");

  const editPlaceSection = document.getElementById("edit-place-section");
  const editPlaceForm = document.getElementById("edit-place-form");
  const editPlaceFormTitle = document.getElementById("edit-place-form-title");
  const editNameInput = document.getElementById("edit-name");
  const editAddressInput = document.getElementById("edit-address-input");
  const editFindCoordsBtn = document.getElementById("edit-find-coords-btn");
  const editGeocodeStatus = document.getElementById("edit-geocode-status");
  const editCoordsSection = document.getElementById("edit-coords-section");
  const editDisplayLat = document.getElementById("edit-display-lat");
  const editDisplayLon = document.getElementById("edit-display-lon");
  const editLatitudeInput = document.getElementById("edit-latitude");
  const editLongitudeInput = document.getElementById("edit-longitude");
  const editAddressHidden = document.getElementById("edit-address");
  const editCityHidden = document.getElementById("edit-city");
  const editCountryHidden = document.getElementById("edit-country");
  const editCategorySelect = document.getElementById("edit-category");
  const editStatusSelect = document.getElementById("edit-status");
  const editReviewTitleInput = document.getElementById("edit-review-title");
  const editReviewTextInput = document.getElementById("edit-review-text");
  const editRatingStarsContainer = document.getElementById("edit-rating-stars");
  const editRatingInput = document.getElementById("edit-rating");
  const editRemoveImageCheckbox = document.getElementById("edit-remove-image");
  const editSubmitBtn = document.getElementById("edit-place-submit-btn");

  const reviewImageSection = document.getElementById("review-image-section");
  const reviewImageForm = document.getElementById("review-image-form");
  const reviewFormTitle = document.getElementById("review-form-title");
  const reviewTitleInput = document.getElementById("review-title");
  const reviewTextInput = document.getElementById("review-text");
  const reviewRatingStarsContainer = document.getElementById(
    "review-rating-stars"
  );
  const reviewRatingInput = document.getElementById("review-rating");
  const reviewImageInput = document.getElementById("review-image");
  const reviewRemoveImageCheckbox = document.getElementById(
    "review-remove-image"
  );
  const currentImageReviewSection = document.getElementById(
    "current-image-review-section"
  );
  const currentImageReviewThumb = document.getElementById(
    "current-image-review-thumb"
  );
  const reviewSubmitBtn = document.getElementById("review-image-submit-btn");

  const seeReviewSection = document.getElementById("see-review-section");
  const seeReviewPlaceTitle = document.getElementById("see-review-place-title");
  const seeReviewRatingDisplay = document.getElementById(
    "see-review-rating-display"
  );
  const seeReviewDisplayTitle = document.getElementById(
    "see-review-display-title"
  );
  const seeReviewDisplayText = document.getElementById(
    "see-review-display-text"
  );
  const seeReviewDisplayImage = document.getElementById(
    "see-review-display-image"
  );
  const seeReviewEditBtn = document.getElementById("see-review-edit-btn");
  const logoutForm = document.getElementById("logout-form"); // Get logout form

  console.log("DOM Loaded, JS Initializing...");
  console.log("User logged in:", window.appConfig?.isUserLoggedIn);

  // --- Initialize Leaflet Map ---
  // More robust way to wait for Leaflet map instance from Folium
  function findLeafletMapInstance(element) {
    if (element._leaflet_map) {
      return element._leaflet_map;
    }
    for (let i = 0; i < element.children.length; i++) {
      const childMap = findLeafletMapInstance(element.children[i]);
      if (childMap) {
        return childMap;
      }
    }
    return null;
  }

  function initializeMapReference() {
    const mapDiv = document.getElementById("map");
    if (!mapDiv) {
      console.error("Map container #map not found.");
      return;
    }

    // Try finding the map instance immediately
    leafletMap = findLeafletMapInstance(mapDiv);

    if (leafletMap) {
      console.log("Leaflet map instance found:", leafletMap);
      // Make sure map container doesn't capture clicks intended for overlays
      leafletMap.getContainer().style.pointerEvents = "auto";
    } else {
      // If not found immediately, set up a MutationObserver to wait for it
      console.log("Waiting for Leaflet map instance via MutationObserver...");
      const observer = new MutationObserver((mutationsList, obs) => {
        leafletMap = findLeafletMapInstance(mapDiv);
        if (leafletMap) {
          console.log(
            "Leaflet map instance found via MutationObserver:",
            leafletMap
          );
          leafletMap.getContainer().style.pointerEvents = "auto";
          obs.disconnect(); // Stop observing once found
        }
      });
      observer.observe(mapDiv, { childList: true, subtree: true });
      // Timeout as a fallback
      setTimeout(() => {
        if (!leafletMap) {
          console.warn("Leaflet map instance not found after timeout.");
          observer.disconnect();
        }
      }, 3000);
    }
  }
  // Initialize only if the map container exists
  if (document.getElementById("map")) {
    initializeMapReference();
  }

  // --- Utility Functions ---
  function setStatusMessage(element, message, type = "info") {
    if (!element) return;
    element.textContent = message;
    element.className = "status-message";
    if (type === "error") element.classList.add("error-message");
    else if (type === "success") element.classList.add("success-message");
    else if (type === "loading") element.classList.add("loading-indicator");
    element.style.display = message ? "block" : "none";
  }

  // --- Authentication Handling ---
  const originalFetch = window.fetch;
  window.fetch = async (...args) => {
    try {
      const response = await originalFetch(...args);
      // Check for 401 specifically on non-login API calls
      const isLoginAttempt = args[0].includes("/api/auth/login");
      if (
        response.status === 401 &&
        !isLoginAttempt &&
        window.location.pathname !== "/login"
      ) {
        console.warn(
          "Received 401 Unauthorized on API call, redirecting to login."
        );
        window.location.href = "/login?session_expired=true";
        // Return a dummy response or throw to prevent further processing in original caller
        return new Response(
          JSON.stringify({ error: "Unauthorized - Session likely expired" }),
          { status: 401 }
        );
      }
      return response;
    } catch (error) {
      console.error("Fetch Interceptor Error:", error);
      throw error;
    }
  };

  // --- Rating Star Logic ---
  function setupRatingStars(containerElement, hiddenInputElement) {
    if (!containerElement || !hiddenInputElement) {
      console.warn(
        "Missing elements for setupRatingStars:",
        containerElement,
        hiddenInputElement
      );
      return;
    }
    const stars = containerElement.querySelectorAll(".star");

    stars.forEach((star) => {
      star.addEventListener("click", (event) => {
        event.stopPropagation(); // Prevent potential conflicts
        const value = star.getAttribute("data-value");
        console.log(
          `Star clicked: value=${value}, target input:`,
          hiddenInputElement.id
        );
        hiddenInputElement.value = value; // Ensure this line works
        updateStarSelection(containerElement, value);
      });

      star.addEventListener("mouseover", (event) => {
        const value = star.getAttribute("data-value");
        highlightStars(containerElement, value);
      });

      star.addEventListener("mouseout", () => {
        updateStarSelection(containerElement, hiddenInputElement.value);
      });
    });

    // Initialize display based on current value
    updateStarSelection(containerElement, hiddenInputElement.value);
  }

  function highlightStars(containerElement, value) {
    if (!containerElement) return;
    const stars = containerElement.querySelectorAll(".star");
    const ratingValue = parseInt(value, 10);

    stars.forEach((star) => {
      const starValue = parseInt(star.getAttribute("data-value"), 10);
      const icon = star.querySelector("i");
      if (!icon) return; // Skip if icon not found

      if (starValue <= ratingValue) {
        icon.classList.remove("far");
        icon.classList.add("fas");
        star.classList.add("selected"); // Use class for hover/selected state consistency
      } else {
        icon.classList.remove("fas");
        icon.classList.add("far");
        star.classList.remove("selected");
      }
    });
  }

  function updateStarSelection(containerElement, selectedValue) {
    if (!containerElement) return;
    const currentRating = parseInt(selectedValue, 10) || 0; // Default to 0 if invalid/empty
    console.log(
      `Updating stars for ${containerElement.id}, selectedValue: ${selectedValue}, parsed rating: ${currentRating}`
    );
    highlightStars(containerElement, currentRating);
  }

  function displayRatingStars(containerElement, rating) {
    if (!containerElement) return;
    const numericRating = parseInt(rating, 10);
    if (numericRating && numericRating >= 1 && numericRating <= 5) {
      let starsHtml = "";
      for (let i = 1; i <= 5; i++) {
        starsHtml += `<i class="${
          i <= numericRating ? "fas" : "far"
        } fa-star"></i> `;
      }
      containerElement.innerHTML = starsHtml.trim(); // Remove trailing space
      containerElement.style.display = "inline-block"; // Use inline-block
    } else {
      containerElement.innerHTML = "(No rating)"; // Indicate no rating
      containerElement.style.display = "inline-block";
    }
  }

  // Initialize star rating inputs on page load
  setupRatingStars(reviewRatingStarsContainer, reviewRatingInput);
  setupRatingStars(editRatingStarsContainer, editRatingInput);

  // --- Geocode & Map Pinning Functions ---
  async function findCoordinates(formType = "add") {
    console.log(`findCoordinates called for form type: ${formType}`);
    if (isPinningMode && formType === "add") {
      togglePinningMode(); // Turn off pinning
    }

    const isEdit = formType === "edit";
    const addressQueryEl = isEdit ? editAddressInput : addressInput;
    const findBtn = isEdit ? editFindCoordsBtn : findCoordsBtn;
    const statusEl = isEdit ? editGeocodeStatus : geocodeStatus;
    const submitButton = isEdit ? editSubmitBtn : addSubmitBtn;

    if (!addressQueryEl || !findBtn || !statusEl || !submitButton) {
      console.error(
        `Geocode Error: Missing elements for form type '${formType}'.`
      );
      setStatusMessage(
        statusEl || geocodeStatus,
        "Internal page error.",
        "error"
      );
      return;
    }

    const addressQuery = addressQueryEl.value.trim();
    if (!addressQuery) {
      setStatusMessage(
        statusEl,
        "Please enter an address or place name.",
        "error"
      );
      return;
    }
    setStatusMessage(statusEl, "Searching...", "loading");
    findBtn.disabled = true;
    if (!isEdit) submitButton.disabled = true;

    try {
      const geocodeBaseUrl = "/geocode";
      const geocodeUrl = `${geocodeBaseUrl}?address=${encodeURIComponent(
        addressQuery
      )}`;
      const response = await fetch(geocodeUrl); // Uses intercepted fetch

      if (response.ok) {
        const result = await response.json();
        updateCoordsDisplay(result, formType); // Update display/hidden fields
        setStatusMessage(
          statusEl,
          `Location found: ${result.display_name}`,
          "success"
        );
        if (!isEdit && hiddenLat.value && hiddenLon.value) {
          // Only enable if coords are valid
          submitButton.disabled = false;
        } else if (
          isEdit &&
          editLatitudeInput.value &&
          editLongitudeInput.value
        ) {
          submitButton.disabled = false;
        }
      } else {
        let errorDetail = `Geocoding failed (${response.status}).`;
        try {
          const d = await response.json();
          errorDetail = d.detail || errorDetail;
        } catch (e) {
          /* ignore */
        }
        setStatusMessage(statusEl, `Error: ${errorDetail}`, "error");
        if (!isEdit) submitButton.disabled = true; // Ensure disabled on failure
      }
    } catch (error) {
      if (error.message?.includes("Unauthorized")) {
        console.error("Geocoding fetch failed due to authorization error.");
        setStatusMessage(
          statusEl,
          "Authentication error. Please log in.",
          "error"
        );
      } else {
        console.error("Geocoding fetch error:", error);
        setStatusMessage(statusEl, "Network error during geocoding.", "error");
      }
      if (!isEdit) submitButton.disabled = true;
    } finally {
      if (findBtn) findBtn.disabled = false;
    }
  }

  function updateCoordsDisplay(coordsData, formType = "add") {
    const isEdit = formType === "edit";
    const coordsSect = isEdit ? editCoordsSection : coordsSection;
    const dispLatEl = isEdit ? editDisplayLat : displayLat;
    const dispLonEl = isEdit ? editDisplayLon : displayLon;
    const dispAddrEl = isEdit ? null : displayAddress;
    const latInput = isEdit ? editLatitudeInput : hiddenLat;
    const lonInput = isEdit ? editLongitudeInput : hiddenLon;
    const addrHidden = isEdit ? editAddressHidden : hiddenAddress;
    const cityHidden = isEdit ? editCityHidden : hiddenCity;
    const countryHidden = isEdit ? editCountryHidden : hiddenCountry;
    const submitButton = isEdit ? editSubmitBtn : addSubmitBtn;

    if (
      !coordsSect ||
      !dispLatEl ||
      !dispLonEl ||
      !latInput ||
      !lonInput ||
      !addrHidden ||
      !cityHidden ||
      !countryHidden ||
      !submitButton
    ) {
      console.error(
        "Cannot update coords display: Missing required elements for form type",
        formType
      );
      return;
    }

    const lat = parseFloat(coordsData.latitude);
    const lon = parseFloat(coordsData.longitude);

    if (isNaN(lat) || isNaN(lon)) {
      console.error("Invalid coordinates received:", coordsData);
      setStatusMessage(
        isEdit ? editGeocodeStatus : geocodeStatus,
        "Invalid coordinate data received.",
        "error"
      );
      submitButton.disabled = true;
      return;
    }

    latInput.value = lat;
    lonInput.value = lon;
    addrHidden.value = coordsData.address || "";
    cityHidden.value = coordsData.city || "";
    countryHidden.value = coordsData.country || "";

    dispLatEl.textContent = lat.toFixed(6);
    dispLonEl.textContent = lon.toFixed(6);

    if (dispAddrEl) {
      dispAddrEl.textContent =
        coordsData.display_name || "(Coordinates set manually)";
    }

    coordsSect.style.display = "block";
    // Enable submit only if we have valid coords now
    submitButton.disabled = !(latInput.value && lonInput.value);
  }

  function handleMapClick(e) {
    if (!isPinningMode || !leafletMap) return;
    const { lat, lng } = e.latlng;
    console.log("Map clicked for pinning at:", lat, lng);

    if (temporaryMarker) {
      leafletMap.removeLayer(temporaryMarker);
    }

    temporaryMarker = L.marker([lat, lng], { draggable: true })
      .addTo(leafletMap)
      .bindPopup("Selected Location. Drag to adjust.")
      .openPopup();

    temporaryMarker.on("dragend", function (event) {
      const marker = event.target;
      const position = marker.getLatLng();
      console.log("Marker dragged to:", position.lat, position.lng);
      updateCoordsFromPin({ latitude: position.lat, longitude: position.lng });
      marker
        .setLatLng(position, { draggable: "true" })
        .bindPopup("Selected Location. Drag to adjust.")
        .update();
    });

    updateCoordsFromPin({ latitude: lat, longitude: lng });
  }

  function updateCoordsFromPin(coords) {
    updateCoordsDisplay(coords, "add");
    setStatusMessage(geocodeStatus, "Location pinned on map.", "success");
    if (addressInput) addressInput.value = "";
    if (addSubmitBtn && hiddenLat.value && hiddenLon.value) {
      // Double check coords are set
      addSubmitBtn.disabled = false;
    } else if (addSubmitBtn) {
      addSubmitBtn.disabled = true; // Disable if coords somehow became invalid
      console.warn("Submit button disabled after pin - coordinates missing?");
    }
  }

  function togglePinningMode() {
    // Use the LEAFLET map instance now
    if (!leafletMap) {
      console.error("Leaflet map instance not available for pinning.");
      setStatusMessage(
        geocodeStatus,
        "Map not ready, cannot pin location.",
        "error"
      );
      return;
    }
    isPinningMode = !isPinningMode;
    const mapContainer = leafletMap.getContainer();

    if (isPinningMode) {
      console.log("Entering map pinning mode.");
      if (addressInput) addressInput.disabled = true;
      if (findCoordsBtn) findCoordsBtn.disabled = true;
      if (mapPinInstruction) mapPinInstruction.style.display = "block";
      mapContainer.style.cursor = "crosshair";
      mapClickHandler = handleMapClick;
      leafletMap.on("click", mapClickHandler);
      if (pinOnMapBtn) pinOnMapBtn.textContent = "Cancel Pinning";
      setStatusMessage(
        geocodeStatus,
        "Click the map to set the place location.",
        "info"
      );
    } else {
      console.log("Exiting map pinning mode.");
      if (addressInput) addressInput.disabled = false;
      if (findCoordsBtn) findCoordsBtn.disabled = false;
      if (mapPinInstruction) mapPinInstruction.style.display = "none";
      mapContainer.style.cursor = "";
      if (mapClickHandler) {
        leafletMap.off("click", mapClickHandler);
        mapClickHandler = null;
      }
      if (temporaryMarker) {
        leafletMap.removeLayer(temporaryMarker);
        temporaryMarker = null;
      }
      if (pinOnMapBtn) pinOnMapBtn.textContent = "Pin Location on Map";
      // If exiting pinning mode *without* setting coords via pin, re-disable submit
      if (addSubmitBtn && (!hiddenLat.value || !hiddenLon.value)) {
        addSubmitBtn.disabled = true;
      }
    }
  }

  // --- Form Display Functions ---
  function hideAllForms() {
    if (addPlaceWrapper) addPlaceWrapper.style.display = "none";
    if (editPlaceSection) editPlaceSection.style.display = "none";
    if (reviewImageSection) reviewImageSection.style.display = "none";
    if (seeReviewSection) seeReviewSection.style.display = "none";
    if (toggleAddPlaceBtn) toggleAddPlaceBtn.textContent = "Add New Place";
    if (isPinningMode) togglePinningMode(); // Ensure pinning mode is off
  }

  function resetAddPlaceCoords() {
    if (coordsSection) coordsSection.style.display = "none";
    setStatusMessage(geocodeStatus, "");
    if (hiddenLat) hiddenLat.value = "";
    if (hiddenLon) hiddenLon.value = "";
    if (hiddenAddress) hiddenAddress.value = "";
    if (hiddenCity) hiddenCity.value = "";
    if (hiddenCountry) hiddenCountry.value = "";
    if (addSubmitBtn) addSubmitBtn.disabled = true;
    if (displayLat) displayLat.textContent = "";
    if (displayLon) displayLon.textContent = "";
    if (displayAddress) displayAddress.textContent = "";
  }

  function resetAddPlaceForm() {
    if (addPlaceForm) addPlaceForm.reset();
    resetAddPlaceCoords();
    if (isPinningMode) togglePinningMode();
  }

  // --- Global Functions Exposed to Inline Event Handlers ---
  window.showAddPlaceForm = function () {
    hideAllForms();
    resetAddPlaceForm();
    if (addPlaceWrapper) {
      addPlaceWrapper.style.display = "block";
      if (toggleAddPlaceBtn) toggleAddPlaceBtn.textContent = "Cancel Adding";
      addPlaceWrapper.scrollIntoView({ behavior: "smooth", block: "start" });
    }
  };

  window.hideAddPlaceForm = function () {
    if (addPlaceWrapper) addPlaceWrapper.style.display = "none";
    if (toggleAddPlaceBtn) toggleAddPlaceBtn.textContent = "Add New Place";
    resetAddPlaceForm();
  };

  window.showEditPlaceForm = function (placeDataJSONString) {
    console.log("Global showEditPlaceForm called.");
    let placeData;
    try {
      placeData = JSON.parse(placeDataJSONString);
    } catch (e) {
      console.error("Error parsing placeData JSON for edit:", e);
      alert("Error reading place data.");
      return;
    }

    const requiredElements = [
      editPlaceSection,
      editPlaceForm,
      editPlaceFormTitle,
      editNameInput,
      editCategorySelect,
      editStatusSelect,
      editAddressInput,
      editDisplayLat,
      editDisplayLon,
      editLatitudeInput,
      editLongitudeInput,
      editAddressHidden,
      editCityHidden,
      editCountryHidden,
      editGeocodeStatus,
      editSubmitBtn,
      editCoordsSection,
      editReviewTitleInput,
      editReviewTextInput,
      editRatingStarsContainer,
      editRatingInput,
      editRemoveImageCheckbox,
    ];
    if (requiredElements.some((el) => !el)) {
      console.error("CRITICAL: One or more Edit Form elements are missing!");
      alert("Error: Edit form elements missing.");
      return;
    }

    try {
      editPlaceFormTitle.textContent = placeData.name || "Unknown";
      editNameInput.value = placeData.name || "";
      editCategorySelect.value = placeData.category || "other";
      editStatusSelect.value = placeData.status || "pending";
      editAddressInput.value = ""; // Clear re-geocode input
      editDisplayLat.textContent = placeData.latitude?.toFixed(6) ?? "N/A";
      editDisplayLon.textContent = placeData.longitude?.toFixed(6) ?? "N/A";
      editLatitudeInput.value = placeData.latitude || "";
      editLongitudeInput.value = placeData.longitude || "";
      editAddressHidden.value = placeData.address || "";
      editCityHidden.value = placeData.city || "";
      editCountryHidden.value = placeData.country || "";
      setStatusMessage(editGeocodeStatus, "");
      editSubmitBtn.disabled = !(
        editLatitudeInput.value && editLongitudeInput.value
      ); // Enable only if coords valid
      editSubmitBtn.textContent = "Save Changes";
      editPlaceForm.action = `/places/${placeData.id}/edit`;

      editReviewTitleInput.value = placeData.review_title || "";
      editReviewTextInput.value = placeData.review || "";
      editRatingInput.value = placeData.rating || "";
      updateStarSelection(editRatingStarsContainer, placeData.rating);
      editRemoveImageCheckbox.checked = false;

      hideAllForms();
      editPlaceSection.style.display = "block";
      editPlaceSection.scrollIntoView({ behavior: "smooth", block: "start" });
    } catch (e) {
      console.error("Error populating edit form:", e);
      alert("Error preparing edit form.");
    }
  };

  window.hideEditPlaceForm = function () {
    if (editPlaceSection) editPlaceSection.style.display = "none";
    if (
      !addPlaceWrapper?.style.display ||
      addPlaceWrapper.style.display === "none"
    ) {
      if (toggleAddPlaceBtn) toggleAddPlaceBtn.textContent = "Add New Place";
    }
  };

  window.showReviewForm = function (placeDataInput) {
    console.log("Global showReviewForm called.");
    let placeData;
    if (typeof placeDataInput === "string") {
      try {
        placeData = JSON.parse(placeDataInput);
      } catch (e) {
        console.error("Error parsing string input in showReviewForm:", e);
        alert("Internal error: Invalid Data String.");
        return;
      }
    } else if (typeof placeDataInput === "object" && placeDataInput !== null) {
      placeData = placeDataInput;
    } else {
      console.error("Invalid input type for showReviewForm.");
      alert("Internal error: Invalid Data Type.");
      return;
    }

    const requiredElements = [
      reviewImageSection,
      reviewImageForm,
      reviewFormTitle,
      reviewTitleInput,
      reviewTextInput,
      reviewRatingStarsContainer,
      reviewRatingInput,
      reviewImageInput,
      reviewRemoveImageCheckbox,
      currentImageReviewSection,
      currentImageReviewThumb,
      reviewSubmitBtn,
    ];
    if (requiredElements.some((el) => !el)) {
      console.error("CRITICAL: One or more Review Form elements missing!");
      alert("Error: Essential review form elements are missing.");
      return;
    }

    try {
      if (!placeData || !placeData.id) {
        throw new Error("placeData object is invalid or missing ID.");
      }

      reviewFormTitle.textContent = placeData.name || "Unknown";
      reviewTitleInput.value = placeData.review_title || "";
      reviewTextInput.value = placeData.review || "";
      reviewRatingInput.value = placeData.rating || ""; // Set hidden input
      updateStarSelection(reviewRatingStarsContainer, placeData.rating); // Update visual stars
      reviewImageInput.value = "";
      reviewRemoveImageCheckbox.checked = false;

      if (placeData.image_url && placeData.image_url.startsWith("http")) {
        currentImageReviewThumb.src = placeData.image_url;
        currentImageReviewSection.style.display = "block";
      } else {
        currentImageReviewSection.style.display = "none";
        currentImageReviewThumb.src = "";
      }

      reviewSubmitBtn.disabled = false;
      reviewSubmitBtn.textContent = "Save Review & Image";
      reviewImageForm.action = `/places/${placeData.id}/review-image`;

      hideAllForms();
      reviewImageSection.style.display = "block";
      reviewImageSection.scrollIntoView({ behavior: "smooth", block: "start" });
    } catch (e) {
      console.error("Error populating review form fields:", e);
      alert("Internal error: Cannot populate review form.");
    }
  };

  window.hideReviewForm = function () {
    if (reviewImageSection) reviewImageSection.style.display = "none";
    if (
      !addPlaceWrapper?.style.display ||
      addPlaceWrapper.style.display === "none"
    ) {
      if (toggleAddPlaceBtn) toggleAddPlaceBtn.textContent = "Add New Place";
    }
  };

  window.showSeeReviewModal = function (placeDataJSONString) {
    console.log("Global showSeeReviewModal called.");
    let placeData;
    try {
      placeData = JSON.parse(placeDataJSONString);
      if (seeReviewEditBtn) {
        seeReviewEditBtn.setAttribute("data-place-json", placeDataJSONString);
      } else {
        console.error("Could not find seeReviewEditBtn to store data.");
      }
    } catch (e) {
      console.error("Error parsing placeData JSON for see review:", e);
      alert("Error reading place data for review display.");
      if (seeReviewEditBtn) seeReviewEditBtn.removeAttribute("data-place-json");
      return;
    }

    const requiredElements = [
      seeReviewSection,
      seeReviewPlaceTitle,
      seeReviewRatingDisplay,
      seeReviewDisplayTitle,
      seeReviewDisplayText,
      seeReviewDisplayImage,
      seeReviewEditBtn,
    ];
    if (requiredElements.some((el) => !el)) {
      console.error("CRITICAL: One or more See Review modal elements missing!");
      alert("Error: Review display elements are missing.");
      return;
    }

    try {
      seeReviewPlaceTitle.textContent = placeData.name || "Unknown Place";
      displayRatingStars(seeReviewRatingDisplay, placeData.rating);
      seeReviewDisplayTitle.textContent = placeData.review_title || "";
      seeReviewDisplayText.textContent =
        placeData.review ||
        (placeData.review_title || placeData.rating
          ? ""
          : "(No review text entered)");
      seeReviewDisplayTitle.style.display = placeData.review_title
        ? "block"
        : "none";

      if (seeReviewDisplayImage) {
        if (placeData.image_url && placeData.image_url.startsWith("http")) {
          seeReviewDisplayImage.src = placeData.image_url;
          seeReviewDisplayImage.alt = `Image for ${placeData.name || "place"}`;
          seeReviewDisplayImage.style.display = "block";
          seeReviewDisplayImage.onclick = showImageOverlay;
        } else {
          seeReviewDisplayImage.style.display = "none";
          seeReviewDisplayImage.src = "";
          seeReviewDisplayImage.onclick = null;
        }
      }

      hideAllForms();
      seeReviewSection.style.display = "block";
      seeReviewSection.scrollIntoView({ behavior: "smooth", block: "start" });
    } catch (e) {
      console.error("Error populating see review modal:", e);
      alert("Error preparing review display.");
    }
  };

  window.hideSeeReviewModal = function () {
    if (seeReviewSection) seeReviewSection.style.display = "none";
    if (seeReviewEditBtn) seeReviewEditBtn.removeAttribute("data-place-json");
    if (seeReviewDisplayImage) seeReviewDisplayImage.onclick = null;
    if (
      !addPlaceWrapper?.style.display ||
      addPlaceWrapper.style.display === "none"
    ) {
      if (toggleAddPlaceBtn) toggleAddPlaceBtn.textContent = "Add New Place";
    }
  };

  // --- Image Overlay Function ---
  function showImageOverlay(event) {
    const clickedImage = event.target;
    if (
      !clickedImage ||
      !clickedImage.src ||
      !clickedImage.src.startsWith("http")
    )
      return;
    const overlay = document.createElement("div");
    overlay.className = "image-overlay";
    const imageInOverlay = document.createElement("img");
    imageInOverlay.src = clickedImage.src;
    imageInOverlay.alt = clickedImage.alt || "Enlarged review image";
    imageInOverlay.onclick = function (e) {
      e.stopPropagation();
    };
    overlay.appendChild(imageInOverlay);
    overlay.onclick = function () {
      overlay.classList.remove("visible");
      overlay.addEventListener(
        "transitionend",
        () => {
          if (document.body.contains(overlay))
            document.body.removeChild(overlay);
        },
        { once: true }
      );
    };
    document.body.appendChild(overlay);
    setTimeout(() => overlay.classList.add("visible"), 10);
  }

  // --- Event Listeners ---
  if (toggleAddPlaceBtn && addPlaceWrapper) {
    toggleAddPlaceBtn.addEventListener("click", () => {
      if (
        addPlaceWrapper.style.display === "none" ||
        addPlaceWrapper.style.display === ""
      ) {
        showAddPlaceForm();
      } else {
        hideAddPlaceForm();
      }
    });
  }

  if (addPlaceCancelBtn) {
    addPlaceCancelBtn.addEventListener("click", hideAddPlaceForm);
  }
  if (findCoordsBtn) {
    findCoordsBtn.addEventListener("click", () => findCoordinates("add"));
  }
  if (pinOnMapBtn) {
    pinOnMapBtn.addEventListener("click", togglePinningMode);
  } // Attach listener

  if (addPlaceForm) {
    addPlaceForm.addEventListener("submit", (event) => {
      if (!hiddenLat?.value || !hiddenLon?.value) {
        event.preventDefault();
        setStatusMessage(
          geocodeStatus,
          'Location coordinates missing. Use "Find" or "Pin" button first.',
          "error"
        );
        if (addSubmitBtn) addSubmitBtn.disabled = true; // Keep disabled if invalid
        return false;
      }
      if (addSubmitBtn) {
        addSubmitBtn.disabled = true;
        addSubmitBtn.textContent = "Adding...";
      }
      if (isPinningMode) togglePinningMode(); // Exit pinning on submit
    });
  }

  if (editFindCoordsBtn) {
    editFindCoordsBtn.addEventListener("click", () => findCoordinates("edit"));
  }

  if (editPlaceForm) {
    editPlaceForm.addEventListener("click", function (event) {
      if (event.target && event.target.matches("button.cancel-btn")) {
        hideEditPlaceForm();
      }
    });
    editPlaceForm.addEventListener("submit", (event) => {
      if (!editLatitudeInput?.value || !editLongitudeInput?.value) {
        event.preventDefault();
        setStatusMessage(
          editGeocodeStatus,
          "Coordinates missing or invalid.",
          "error"
        );
        if (editSubmitBtn) editSubmitBtn.disabled = true; // Keep disabled
        return false;
      }
      // Convert empty rating string to null before submitting potentially? No, backend handles Optional[int]
      if (editSubmitBtn) {
        editSubmitBtn.disabled = true;
        editSubmitBtn.textContent = "Saving...";
      }
    });
  }

  if (reviewImageForm) {
    reviewImageForm.addEventListener("click", function (event) {
      if (event.target && event.target.matches("button.cancel-btn")) {
        hideReviewForm();
      }
    });
    reviewImageForm.addEventListener("submit", (event) => {
      // Ensure rating is set if stars were clicked
      if (!reviewRatingInput.value) {
        // Optional: Set to empty or handle as needed, Pydantic Optional[int] should handle None
        console.log("Submitting review form with no rating selected.");
      } else if (
        parseInt(reviewRatingInput.value) < 1 ||
        parseInt(reviewRatingInput.value) > 5
      ) {
        event.preventDefault(); // Prevent submit
        alert("Please select a valid rating between 1 and 5 stars."); // Simple feedback
        return false;
      }
      if (reviewSubmitBtn) {
        reviewSubmitBtn.disabled = true;
        reviewSubmitBtn.textContent = "Saving...";
      }
    });
  }

  if (seeReviewSection) {
    seeReviewSection.addEventListener("click", function (event) {
      if (event.target && event.target.matches("button.cancel-btn")) {
        hideSeeReviewModal();
      }
    });
  }

  if (seeReviewEditBtn) {
    seeReviewEditBtn.addEventListener("click", (event) => {
      const button = event.target;
      const placeDataJSONString = button.getAttribute("data-place-json");
      if (placeDataJSONString) {
        try {
          const placeDataObject = JSON.parse(placeDataJSONString);
          window.showReviewForm(placeDataObject); // Show review form for editing
        } catch (e) {
          console.error(
            "Error parsing placeData JSON from button attribute:",
            e
          );
          alert("Error reading data needed to edit review.");
        }
      } else {
        console.error("Cannot edit review, data attribute missing.");
        alert("Error: Could not retrieve data to edit review.");
      }
    });
  }

  // Handle Logout Form Submission with JS
  if (logoutForm) {
    logoutForm.addEventListener("submit", async (event) => {
      event.preventDefault(); // Prevent standard form submission
      console.log("Logout form submitted via JS");
      try {
        // Call the API endpoint
        const response = await fetch(logoutForm.action, {
          // Use form action URL
          method: "POST",
          // No body needed, auth determined by cookie
        });

        if (response.ok || response.status === 303) {
          // Handle redirect status as ok here
          // API call succeeded (cookie deleted on backend)
          console.log("Logout API call successful.");
          // Redirect to login page on client-side
          window.location.href = "/login?logged_out=true";
        } else {
          // Handle potential errors from API call
          console.error(
            "Logout API call failed:",
            response.status,
            response.statusText
          );
          alert("Logout failed. Please try again.");
        }
      } catch (error) {
        console.error("Error during logout fetch:", error);
        alert("An error occurred during logout.");
      }
    });
  }

  // Initial state setup
  hideAllForms();
  if (addSubmitBtn) addSubmitBtn.disabled = true;

  console.log("JS Initialization Complete. Event listeners attached.");
}); // End of DOMContentLoaded listener
