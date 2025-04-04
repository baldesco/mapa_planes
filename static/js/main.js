document.addEventListener("DOMContentLoaded", function () {
  // --- Global Variables & State ---
  let leafletMap = null; // Explicitly store Leaflet map instance
  let mapClickHandler = null;
  let isPinningMode = false;
  let temporaryMarker = null;
  let isEditPinningMode = false; // State for edit form pinning
  let editMapClickHandler = null; // Handler for edit map clicks
  const MAP_RETRY_DELAY = 300; // ms between retries
  const MAX_MAP_RETRIES = 5; // Max attempts to find map

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
  const editPinOnMapBtn = document.getElementById("edit-pin-on-map-btn");
  const editMapPinInstruction = document.getElementById(
    "edit-map-pin-instruction"
  );

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
  const logoutButton = document.getElementById("logout-btn");

  console.log("DOM Loaded, JS Initializing...");
  console.log("User logged in:", window.appConfig?.isUserLoggedIn);

  // --- Leaflet Map Initialization ---
  function findLeafletMapInstance(element) {
    if (!element) return null;
    if (element._leaflet_map) {
      // console.debug("Found map instance via _leaflet_map property");
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

  // Function to get map instance, storing it globally if found
  function getMapInstance() {
    if (leafletMap) {
      return leafletMap;
    }
    const mapDiv = document.getElementById("map");
    if (!mapDiv) {
      console.error("Map container #map not found.");
      return null;
    }
    leafletMap = findLeafletMapInstance(mapDiv);
    if (leafletMap) {
      console.log("Leaflet map instance obtained:", leafletMap);
      try {
        leafletMap.getContainer().style.pointerEvents = "auto";
      } catch (e) {
        console.warn("Could not set pointerEvents on map container:", e);
      }
    }
    // No warning here, happens often on initial load
    return leafletMap;
  }

  // Async function to get map instance with retries
  async function ensureMapReadyWithRetries(retryCount = 0) {
    const currentMap = getMapInstance();
    if (currentMap) {
      return currentMap;
    }
    if (retryCount >= MAX_MAP_RETRIES) {
      console.error(`Map instance not found after ${MAX_MAP_RETRIES} retries.`);
      return null;
    }

    console.log(
      `Map not ready, retrying in ${MAP_RETRY_DELAY}ms (attempt ${
        retryCount + 1
      })`
    );
    await new Promise((resolve) => setTimeout(resolve, MAP_RETRY_DELAY));
    return ensureMapReadyWithRetries(retryCount + 1); // Recursive call
  }

  // Attempt to get map reference on initial load (best effort, no retry here)
  if (document.getElementById("map")) {
    setTimeout(getMapInstance, 500); // Slightly longer delay
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
      const isLoginAttempt = args[0].includes("/api/auth/login");
      if (
        response.status === 401 &&
        !isLoginAttempt &&
        window.location.pathname !== "/login"
      ) {
        console.warn(
          "Received 401 Unauthorized on API call, redirecting to login."
        );
        // Add parameter to show message on login page
        window.location.href = "/login?reason=session_expired";
        return new Response(
          JSON.stringify({ error: "Unauthorized - Session likely expired" }),
          { status: 401 }
        );
      }
      return response;
    } catch (error) {
      console.error("Fetch Interceptor Error:", error);
      // Check if it's a network error potentially indicating server down
      if (error instanceof TypeError && error.message === "Failed to fetch") {
        console.error("Network error: Could not connect to the server.");
      }
      throw error;
    }
  };

  // --- Rating Star Logic ---
  function setupRatingStars(containerElement, hiddenInputElement) {
    if (!containerElement || !hiddenInputElement) {
      return;
    }
    const stars = containerElement.querySelectorAll(".star");

    stars.forEach((star) => {
      star.addEventListener("click", (event) => {
        event.stopPropagation();
        const value = star.getAttribute("data-value");
        hiddenInputElement.value = value;
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
    updateStarSelection(containerElement, hiddenInputElement.value);
  }

  function highlightStars(containerElement, value) {
    if (!containerElement) return;
    const stars = containerElement.querySelectorAll(".star");
    const ratingValue = parseInt(value, 10);

    stars.forEach((star) => {
      const starValue = parseInt(star.getAttribute("data-value"), 10);
      const icon = star.querySelector("i");
      if (!icon) return;

      if (starValue <= ratingValue) {
        icon.classList.remove("far");
        icon.classList.add("fas");
        star.classList.add("selected");
      } else {
        icon.classList.remove("fas");
        icon.classList.add("far");
        star.classList.remove("selected");
      }
    });
  }

  function updateStarSelection(containerElement, selectedValue) {
    if (!containerElement) return;
    const currentRating = parseInt(selectedValue, 10) || 0;
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
      containerElement.innerHTML = starsHtml.trim();
      containerElement.style.display = "inline-block";
    } else {
      containerElement.innerHTML = "(No rating)";
      containerElement.style.display = "inline-block";
    }
  }

  setupRatingStars(reviewRatingStarsContainer, reviewRatingInput);
  setupRatingStars(editRatingStarsContainer, editRatingInput);

  // --- Geocode & Map Pinning Functions ---
  async function findCoordinates(formType = "add") {
    console.log(`findCoordinates called for form type: ${formType}`);

    if (formType === "add" && isPinningMode) {
      await togglePinningMode();
    } else if (formType === "edit" && isEditPinningMode) {
      await toggleEditPinningMode();
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
    submitButton.disabled = true;

    try {
      const geocodeBaseUrl = "/geocode";
      const geocodeUrl = `${geocodeBaseUrl}?address=${encodeURIComponent(
        addressQuery
      )}`;
      const response = await fetch(geocodeUrl);

      if (response.ok) {
        const result = await response.json();
        updateCoordsDisplay(result, formType);
        setStatusMessage(
          statusEl,
          `Location found: ${result.display_name}`,
          "success"
        );
        const latVal = isEdit ? editLatitudeInput.value : hiddenLat.value;
        const lonVal = isEdit ? editLongitudeInput.value : hiddenLon.value;
        if (latVal && lonVal) {
          submitButton.disabled = false;
        } else {
          submitButton.disabled = true;
        }
      } else {
        let errorDetail = `Geocoding failed (${response.status}).`;
        try {
          const d = await response.json();
          errorDetail = d.detail || errorDetail;
        } catch (e) {}
        setStatusMessage(statusEl, `Error: ${errorDetail}`, "error");
        submitButton.disabled = true;
      }
    } catch (error) {
      if (error.message?.includes("Unauthorized")) {
        setStatusMessage(
          statusEl,
          "Authentication error. Please log in.",
          "error"
        );
      } else {
        setStatusMessage(statusEl, "Network error during geocoding.", "error");
      }
      submitButton.disabled = true;
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
    const statusEl = isEdit ? editGeocodeStatus : geocodeStatus;

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
      setStatusMessage(statusEl, "Invalid coordinate data received.", "error");
      submitButton.disabled = true;
      latInput.value = "";
      lonInput.value = "";
      dispLatEl.textContent = "";
      dispLonEl.textContent = "";
      return;
    }

    latInput.value = lat;
    lonInput.value = lon;
    if (
      coordsData.display_name !== undefined ||
      coordsData.address !== undefined
    ) {
      addrHidden.value = coordsData.address || "";
      cityHidden.value = coordsData.city || "";
      countryHidden.value = coordsData.country || "";
    }

    dispLatEl.textContent = lat.toFixed(6);
    dispLonEl.textContent = lon.toFixed(6);

    if (dispAddrEl) {
      dispAddrEl.textContent =
        coordsData.display_name || "(Coordinates set manually)";
    }

    coordsSect.style.display = "block";
    submitButton.disabled = !(latInput.value && lonInput.value);
  }

  function handleMapClick(e) {
    const currentMap = getMapInstance();
    if (!isPinningMode || !currentMap) return;
    const { lat, lng } = e.latlng;
    placeTemporaryMarker(lat, lng, "add");
    updateCoordsFromPin({ latitude: lat, longitude: lng }, "add");
  }

  function handleEditMapClick(e) {
    const currentMap = getMapInstance();
    if (!isEditPinningMode || !currentMap) return;
    const { lat, lng } = e.latlng;
    placeTemporaryMarker(lat, lng, "edit");
    updateCoordsFromPin({ latitude: lat, longitude: lng }, "edit");
  }

  function placeTemporaryMarker(lat, lng, formType = "add") {
    const currentMap = getMapInstance();
    if (!currentMap) {
      console.error(
        `Cannot place marker (${formType}): Map instance not available.`
      );
      return;
    }

    if (temporaryMarker) {
      currentMap.removeLayer(temporaryMarker);
    }

    temporaryMarker = L.marker([lat, lng], { draggable: true })
      .addTo(currentMap)
      .bindPopup("Selected Location. Drag to adjust.")
      .openPopup();

    temporaryMarker.on("dragend", function (event) {
      const marker = event.target;
      const position = marker.getLatLng();
      updateCoordsFromPin(
        { latitude: position.lat, longitude: position.lng, address: undefined },
        formType
      );
      marker
        .setLatLng(position)
        .bindPopup("Selected Location. Drag to adjust.")
        .openPopup();
    });
  }

  function updateCoordsFromPin(coords, formType = "add") {
    const isEdit = formType === "edit";
    const statusEl = isEdit ? editGeocodeStatus : geocodeStatus;
    const addressQueryEl = isEdit ? editAddressInput : addressInput;
    const submitButton = isEdit ? editSubmitBtn : addSubmitBtn;

    updateCoordsDisplay(coords, formType);
    setStatusMessage(statusEl, "Location pinned on map.", "success");
    if (addressQueryEl) addressQueryEl.value = "";

    const latVal = isEdit ? editLatitudeInput.value : hiddenLat.value;
    const lonVal = isEdit ? editLongitudeInput.value : hiddenLon.value;
    if (submitButton) {
      submitButton.disabled = !(latVal && lonVal);
    }
  }

  // --- Pinning Mode Toggles ---
  async function togglePinningMode() {
    // Use retry mechanism specifically when toggling
    const currentMap = await ensureMapReadyWithRetries();
    if (!currentMap) {
      setStatusMessage(
        geocodeStatus,
        "Map not ready, cannot pin location. Please wait a moment and try again.",
        "error"
      );
      console.error(
        "togglePinningMode: Map instance not available after retries."
      );
      return; // Exit if map not ready
    }

    if (isEditPinningMode) {
      await toggleEditPinningMode(); // Turn off edit pinning first
    }

    isPinningMode = !isPinningMode;
    const mapContainer = currentMap.getContainer();

    if (isPinningMode) {
      console.log("Entering ADD form map pinning mode.");
      if (addressInput) addressInput.disabled = true;
      if (findCoordsBtn) findCoordsBtn.disabled = true;
      if (mapPinInstruction) mapPinInstruction.style.display = "block";
      mapContainer.style.cursor = "crosshair";
      mapClickHandler = handleMapClick;
      currentMap.on("click", mapClickHandler);
      if (pinOnMapBtn) pinOnMapBtn.textContent = "Cancel Pinning";
      setStatusMessage(
        geocodeStatus,
        "Click the map to set the place location.",
        "info"
      );
    } else {
      console.log("Exiting ADD form map pinning mode.");
      if (addressInput) addressInput.disabled = false;
      if (findCoordsBtn) findCoordsBtn.disabled = false;
      if (mapPinInstruction) mapPinInstruction.style.display = "none";
      mapContainer.style.cursor = "";
      if (mapClickHandler) {
        currentMap.off("click", mapClickHandler);
        mapClickHandler = null;
      }
      if (temporaryMarker) {
        currentMap.removeLayer(temporaryMarker);
        temporaryMarker = null;
      }
      if (pinOnMapBtn) pinOnMapBtn.textContent = "Pin Location on Map";
      if (addSubmitBtn) {
        addSubmitBtn.disabled = !(hiddenLat.value && hiddenLon.value);
      }
    }
  }

  async function toggleEditPinningMode() {
    // Use retry mechanism specifically when toggling
    const currentMap = await ensureMapReadyWithRetries();
    if (!currentMap) {
      setStatusMessage(
        editGeocodeStatus,
        "Map not ready, cannot pin location. Please wait a moment and try again.",
        "error"
      );
      console.error(
        "toggleEditPinningMode: Map instance not available after retries."
      );
      return; // Exit if map not ready
    }

    if (isPinningMode) {
      await togglePinningMode(); // Turn off add pinning first
    }

    isEditPinningMode = !isEditPinningMode;
    const mapContainer = currentMap.getContainer();

    if (isEditPinningMode) {
      console.log("Entering EDIT form map pinning mode.");
      if (editAddressInput) editAddressInput.disabled = true;
      if (editFindCoordsBtn) editFindCoordsBtn.disabled = true;
      if (editMapPinInstruction) editMapPinInstruction.style.display = "block";
      mapContainer.style.cursor = "crosshair";
      editMapClickHandler = handleEditMapClick;
      currentMap.on("click", editMapClickHandler);
      if (editPinOnMapBtn) editPinOnMapBtn.textContent = "Cancel Pinning";
      setStatusMessage(
        editGeocodeStatus,
        "Click the map to set the new location, or drag the marker.",
        "info"
      );

      const currentLat = parseFloat(editLatitudeInput.value);
      const currentLon = parseFloat(editLongitudeInput.value);
      if (!isNaN(currentLat) && !isNaN(currentLon)) {
        placeTemporaryMarker(currentLat, currentLon, "edit");
      } else {
        // Optionally place marker at map center if current coords invalid?
        // const center = currentMap.getCenter();
        // placeTemporaryMarker(center.lat, center.lng, "edit");
        console.warn(
          "Cannot place initial edit marker: invalid coords. Click map to set."
        );
      }
    } else {
      console.log("Exiting EDIT form map pinning mode.");
      if (editAddressInput) editAddressInput.disabled = false;
      if (editFindCoordsBtn) editFindCoordsBtn.disabled = false;
      if (editMapPinInstruction) editMapPinInstruction.style.display = "none";
      mapContainer.style.cursor = "";
      if (editMapClickHandler) {
        currentMap.off("click", editMapClickHandler);
        editMapClickHandler = null;
      }
      if (temporaryMarker) {
        currentMap.removeLayer(temporaryMarker);
        temporaryMarker = null;
      }
      if (editPinOnMapBtn) editPinOnMapBtn.textContent = "Pin Location on Map";
      if (editSubmitBtn) {
        editSubmitBtn.disabled = !(
          editLatitudeInput.value && editLongitudeInput.value
        );
      }
    }
  }

  // --- Form Display Functions ---
  async function hideAllForms() {
    // Made async to await toggles
    if (addPlaceWrapper) addPlaceWrapper.style.display = "none";
    if (editPlaceSection) editPlaceSection.style.display = "none";
    if (reviewImageSection) reviewImageSection.style.display = "none";
    if (seeReviewSection) seeReviewSection.style.display = "none";
    if (toggleAddPlaceBtn) toggleAddPlaceBtn.textContent = "Add New Place";

    // Ensure pinning modes are off when hiding forms
    // Check flags before calling toggle to avoid infinite loops
    if (isPinningMode) {
      console.debug("Hiding forms, turning off ADD pinning mode.");
      await togglePinningMode(); // await ensures it finishes
    }
    if (isEditPinningMode) {
      console.debug("Hiding forms, turning off EDIT pinning mode.");
      await toggleEditPinningMode(); // await ensures it finishes
    }
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
    if (addressInput) addressInput.value = "";
  }

  function resetAddPlaceForm() {
    if (addPlaceForm) addPlaceForm.reset();
    resetAddPlaceCoords();
  }

  // --- Global Functions Exposed to Inline Event Handlers ---
  window.showAddPlaceForm = async function () {
    // Made async
    await hideAllForms(); // await ensures pinning modes are off
    resetAddPlaceForm();
    if (addPlaceWrapper) {
      addPlaceWrapper.style.display = "block";
      if (toggleAddPlaceBtn) toggleAddPlaceBtn.textContent = "Cancel Adding";
      addPlaceWrapper.scrollIntoView({ behavior: "smooth", block: "start" });
    }
  };

  window.hideAddPlaceForm = async function () {
    // Made async
    if (addPlaceWrapper) addPlaceWrapper.style.display = "none";
    if (toggleAddPlaceBtn) toggleAddPlaceBtn.textContent = "Add New Place";
    // Ensure pinning is off
    if (isPinningMode) {
      await togglePinningMode();
    }
    // resetAddPlaceForm(); // Consider if reset is needed on explicit cancel
  };

  window.showEditPlaceForm = async function (placeDataJSONString) {
    // Made async
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
      editPinOnMapBtn,
      editMapPinInstruction,
    ];
    if (requiredElements.some((el) => !el)) {
      console.error("CRITICAL: One or more Edit Form elements are missing!");
      alert("Error: Edit form elements missing.");
      return;
    }

    await hideAllForms(); // Hide other forms and cancel their pinning modes

    try {
      editPlaceFormTitle.textContent = placeData.name || "Unknown";
      editNameInput.value = placeData.name || "";
      editCategorySelect.value = placeData.category || "other";
      editStatusSelect.value = placeData.status || "pending";
      editAddressInput.value = "";
      editAddressInput.disabled = false;
      editFindCoordsBtn.disabled = false;
      editPinOnMapBtn.textContent = "Pin Location on Map";
      editMapPinInstruction.style.display = "none";

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
      );
      editSubmitBtn.textContent = "Save Changes";
      editPlaceForm.action = `/places/${placeData.id}/edit`;

      editReviewTitleInput.value = placeData.review_title || "";
      editReviewTextInput.value = placeData.review || "";
      editRatingInput.value = placeData.rating || "";
      updateStarSelection(editRatingStarsContainer, placeData.rating);
      editRemoveImageCheckbox.checked = false;

      editPlaceSection.style.display = "block";
      editPlaceSection.scrollIntoView({ behavior: "smooth", block: "start" });
    } catch (e) {
      console.error("Error populating edit form:", e);
      alert("Error preparing edit form.");
    }
  };

  window.hideEditPlaceForm = async function () {
    // Made async
    if (editPlaceSection) editPlaceSection.style.display = "none";
    if (isEditPinningMode) {
      console.debug("Hiding Edit form, turning off EDIT pinning mode.");
      await toggleEditPinningMode(); // await ensures it finishes
    }
    if (
      !addPlaceWrapper?.style.display ||
      addPlaceWrapper.style.display === "none"
    ) {
      if (toggleAddPlaceBtn) toggleAddPlaceBtn.textContent = "Add New Place";
    }
  };

  window.showReviewForm = async function (placeDataInput) {
    // Made async
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

    await hideAllForms(); // Hide other forms first

    try {
      if (!placeData || !placeData.id) {
        throw new Error("placeData object is invalid or missing ID.");
      }

      reviewFormTitle.textContent = placeData.name || "Unknown";
      reviewTitleInput.value = placeData.review_title || "";
      reviewTextInput.value = placeData.review || "";
      reviewRatingInput.value = placeData.rating || "";
      updateStarSelection(reviewRatingStarsContainer, placeData.rating);
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

  window.showSeeReviewModal = async function (placeDataJSONString) {
    // Made async
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

    await hideAllForms(); // Hide other forms first

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
    let overlay = document.querySelector(".image-overlay");
    if (!overlay) {
      overlay = document.createElement("div");
      overlay.className = "image-overlay";
      const imageInOverlay = document.createElement("img");
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
    }
    const imageInOverlay = overlay.querySelector("img");
    if (imageInOverlay) imageInOverlay.src = clickedImage.src; // Always set src
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
  }

  if (addPlaceForm) {
    addPlaceForm.addEventListener("submit", (event) => {
      if (!hiddenLat?.value || !hiddenLon?.value) {
        event.preventDefault();
        setStatusMessage(
          geocodeStatus,
          'Location coordinates missing. Use "Find" or "Pin" button first.',
          "error"
        );
        if (addSubmitBtn) addSubmitBtn.disabled = true;
        return false;
      }
      if (addSubmitBtn) {
        addSubmitBtn.disabled = true;
        addSubmitBtn.textContent = "Adding...";
      }
    });
  }

  if (editFindCoordsBtn) {
    editFindCoordsBtn.addEventListener("click", () => findCoordinates("edit"));
  }
  if (editPinOnMapBtn) {
    editPinOnMapBtn.addEventListener("click", toggleEditPinningMode);
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
        if (editSubmitBtn) editSubmitBtn.disabled = true;
        return false;
      }
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
      const ratingValue = reviewRatingInput.value;
      if (ratingValue) {
        const ratingNum = parseInt(ratingValue, 10);
        if (isNaN(ratingNum) || ratingNum < 1 || ratingNum > 5) {
          event.preventDefault();
          alert(
            "Please select a valid rating between 1 and 5 stars, or leave it blank."
          );
          return false;
        }
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
          window.showReviewForm(placeDataJSONString);
        } catch (e) {
          alert("Error reading data needed to edit review.");
        }
      } else {
        alert("Error: Could not retrieve data to edit review.");
      }
    });
  }

  // Logout Button Listener
  if (logoutButton) {
    logoutButton.addEventListener("click", async () => {
      console.log("Logout button clicked");
      try {
        const response = await fetch("/api/auth/logout", {
          method: "POST",
        });
        if (response.ok || response.status === 204) {
          console.log("Logout API call successful.");
          window.location.href = "/login?reason=logged_out"; // Force redirect
        } else {
          console.error(
            "Logout API call failed:",
            response.status,
            response.statusText
          );
          try {
            const errorData = await response.json();
            alert(`Logout failed: ${errorData.detail || "Unknown error"}`);
          } catch {
            alert("Logout failed. Please try again.");
          }
        }
      } catch (error) {
        console.error("Error during logout fetch:", error);
        alert("An error occurred during logout.");
      }
    });
  } else {
    console.warn("#logout-btn not found");
  }

  // Initial state setup
  hideAllForms(); // Call initially to set state and cancel any pinning
  if (addSubmitBtn) addSubmitBtn.disabled = true;
  if (editSubmitBtn) editSubmitBtn.disabled = true;

  console.log("JS Initialization Complete. Event listeners attached.");
});
