document.addEventListener("DOMContentLoaded", function () {
  // --- DOM Elements ---
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
  const nameInput = document.getElementById("name"); // Get name input for reset
  const addCategorySelect = document.getElementById("add-category");
  const addStatusSelect = document.getElementById("add-status");

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
  const editSubmitBtn = document.getElementById("edit-place-submit-btn");

  const reviewImageSection = document.getElementById("review-image-section");
  const reviewImageForm = document.getElementById("review-image-form");
  const reviewFormTitle = document.getElementById("review-form-title");
  const reviewTitleInput = document.getElementById("review-title");
  const reviewTextInput = document.getElementById("review-text");
  const reviewImageInput = document.getElementById("review-image");
  const reviewSubmitBtn = document.getElementById("review-image-submit-btn");

  const seeReviewSection = document.getElementById("see-review-section");
  const seeReviewPlaceTitle = document.getElementById("see-review-place-title");
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

  console.log("DOM Loaded, JS Initializing...");

  // --- Utility Functions ---
  function setStatusMessage(element, message, type = "info") {
    if (!element) {
      console.warn("setStatusMessage: Target element not found.");
      return;
    }
    element.textContent = message;
    element.className = "status-message"; // Reset classes first
    if (type === "error") element.classList.add("error-message");
    else if (type === "success") element.classList.add("success-message");
    else if (type === "loading") element.classList.add("loading-indicator");
    element.style.display = message ? "block" : "none";
  }

  // --- Geocode Function ---
  async function findCoordinates(formType = "add") {
    console.log(`findCoordinates called for form type: ${formType}`);
    const isEdit = formType === "edit";
    const addressQueryEl = isEdit ? editAddressInput : addressInput;
    const findBtn = isEdit ? editFindCoordsBtn : findCoordsBtn;
    const statusEl = isEdit ? editGeocodeStatus : geocodeStatus;
    const coordsSect = isEdit ? editCoordsSection : coordsSection;
    const dispLatEl = isEdit ? editDisplayLat : displayLat;
    const dispLonEl = isEdit ? editDisplayLon : displayLon;
    const dispAddrEl = isEdit ? null : displayAddress; // No display name in edit coords section
    const latInput = isEdit ? editLatitudeInput : hiddenLat;
    const lonInput = isEdit ? editLongitudeInput : hiddenLon;
    const addrHidden = isEdit ? editAddressHidden : hiddenAddress;
    const cityHidden = isEdit ? editCityHidden : hiddenCity;
    const countryHidden = isEdit ? editCountryHidden : hiddenCountry;
    const submitButton = isEdit ? editSubmitBtn : addSubmitBtn;

    // Simplified check
    if (
      !addressQueryEl ||
      !findBtn ||
      !statusEl ||
      !latInput ||
      !lonInput ||
      !addrHidden ||
      !cityHidden ||
      !countryHidden ||
      !coordsSect ||
      !submitButton
    ) {
      console.error(
        `Geocode Error: Missing required elements for form type '${formType}'. Cannot proceed.`
      );
      setStatusMessage(
        statusEl || geocodeStatus,
        "Internal page error. Cannot find coordinates.",
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
    if (!isEdit) submitButton.disabled = true; // Only disable Add button initially

    try {
      // Assuming request object is available globally or passed differently
      // In a real scenario, get this base URL from a global JS var or data attribute
      const geocodeBaseUrl = "/geocode"; // Simpler relative URL if served by same FastAPI app
      const geocodeUrl = `${geocodeBaseUrl}?address=${encodeURIComponent(
        addressQuery
      )}`;
      const response = await fetch(geocodeUrl);

      if (response.ok) {
        const result = await response.json();
        let successMsg = `Location found: ${result.display_name}`;
        // For edit form, update coordinates but don't force save enable yet
        setStatusMessage(statusEl, successMsg, "success");

        latInput.value = result.latitude;
        lonInput.value = result.longitude;
        addrHidden.value = result.address || "";
        cityHidden.value = result.city || "";
        countryHidden.value = result.country || "";
        if (dispLatEl)
          dispLatEl.textContent = result.latitude?.toFixed(6) ?? "N/A";
        if (dispLonEl)
          dispLonEl.textContent = result.longitude?.toFixed(6) ?? "N/A";
        if (dispAddrEl) dispAddrEl.textContent = result.display_name; // Only for add form

        if (!isEdit && coordsSect) coordsSect.style.display = "block"; // Show coords for add form
        if (!isEdit) submitButton.disabled = false; // Enable Add button on success
      } else {
        let errorDetail = `Geocoding failed (${response.status}).`;
        try {
          const d = await response.json();
          errorDetail = d.detail || errorDetail;
        } catch (e) {
          /* ignore */
        }
        setStatusMessage(statusEl, `Error: ${errorDetail}`, "error");
        if (!isEdit) submitButton.disabled = true; // Keep Add disabled on error
      }
    } catch (error) {
      console.error("Geocoding fetch error:", error);
      setStatusMessage(statusEl, "Network error during geocoding.", "error");
      if (!isEdit) submitButton.disabled = true; // Keep Add disabled on error
    } finally {
      if (findBtn) findBtn.disabled = false; // Always re-enable find button
    }
  }

  // --- Form Display Functions ---

  function hideAllForms() {
    if (addPlaceWrapper) addPlaceWrapper.style.display = "none";
    if (editPlaceSection) editPlaceSection.style.display = "none";
    if (reviewImageSection) reviewImageSection.style.display = "none";
    if (seeReviewSection) seeReviewSection.style.display = "none";
    if (toggleAddPlaceBtn) toggleAddPlaceBtn.textContent = "Add New Place"; // Reset button text
  }

  function resetAddPlaceForm() {
    if (addPlaceForm) addPlaceForm.reset(); // Standard form reset
    if (coordsSection) coordsSection.style.display = "none"; // Hide coords display
    setStatusMessage(geocodeStatus, ""); // Clear status message
    if (hiddenLat) hiddenLat.value = ""; // Clear hidden coords
    if (hiddenLon) hiddenLon.value = "";
    if (hiddenAddress) hiddenAddress.value = "";
    if (hiddenCity) hiddenCity.value = "";
    if (hiddenCountry) hiddenCountry.value = "";
    if (addSubmitBtn) addSubmitBtn.disabled = true; // Disable submit until coords found
  }

  window.showAddPlaceForm = function () {
    hideAllForms(); // Hide others first
    resetAddPlaceForm(); // Reset fields
    if (addPlaceWrapper) {
      addPlaceWrapper.style.display = "block";
      if (toggleAddPlaceBtn) toggleAddPlaceBtn.textContent = "Cancel Adding";
      addPlaceWrapper.scrollIntoView({ behavior: "smooth", block: "start" });
    }
  };

  window.hideAddPlaceForm = function () {
    if (addPlaceWrapper) addPlaceWrapper.style.display = "none";
    if (toggleAddPlaceBtn) toggleAddPlaceBtn.textContent = "Add New Place";
    resetAddPlaceForm(); // Also reset when hiding
  };

  // Make showEditPlaceForm global
  window.showEditPlaceForm = function (placeDataJSONString) {
    console.log("Global showEditPlaceForm called.");
    let placeData;
    try {
      placeData = JSON.parse(placeDataJSONString);
    } catch (e) {
      console.error(
        "Error parsing placeData JSON for edit:",
        e,
        "String:",
        placeDataJSONString
      );
      alert("Error reading place data.");
      return;
    }

    // Check if all required elements exist
    const requiredEditElements = [
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
    ];
    if (requiredEditElements.some((el) => !el)) {
      console.error(
        "CRITICAL: One or more Edit Form elements are missing!",
        requiredEditElements
      );
      alert("Error: Edit form elements missing.");
      return;
    }

    try {
      editPlaceFormTitle.textContent = placeData.name || "Unknown";
      editNameInput.value = placeData.name || "";
      editCategorySelect.value = placeData.category || "other";
      editStatusSelect.value = placeData.status || "pending";
      editAddressInput.value = ""; // Clear address input for potential re-geocoding
      editDisplayLat.textContent = placeData.latitude?.toFixed(6) ?? "N/A";
      editDisplayLon.textContent = placeData.longitude?.toFixed(6) ?? "N/A";
      editLatitudeInput.value = placeData.latitude || "";
      editLongitudeInput.value = placeData.longitude || "";
      editAddressHidden.value = placeData.address || ""; // Keep current address details unless re-geocoded
      editCityHidden.value = placeData.city || "";
      editCountryHidden.value = placeData.country || "";
      setStatusMessage(editGeocodeStatus, ""); // Clear previous geocode status
      editSubmitBtn.disabled = false;
      editSubmitBtn.textContent = "Save Changes";
      // Construct URL - Ensure endpoint name is correct
      const editUrl = `/places/${placeData.id}/edit`;
      editPlaceForm.action = editUrl;

      hideAllForms(); // Hide other forms
      editPlaceSection.style.display = "block";
      editPlaceSection.scrollIntoView({ behavior: "smooth", block: "start" });
    } catch (e) {
      console.error("Error populating edit form:", e);
      alert("Error preparing edit form.");
    }
  };

  window.hideEditPlaceForm = function () {
    if (editPlaceSection) editPlaceSection.style.display = "none";
    // Optionally show the main toggle button if nothing else is active
    if (
      addPlaceWrapper &&
      addPlaceWrapper.style.display === "none" &&
      reviewImageSection &&
      reviewImageSection.style.display === "none" &&
      seeReviewSection &&
      seeReviewSection.style.display === "none"
    ) {
      if (toggleAddPlaceBtn) toggleAddPlaceBtn.textContent = "Add New Place";
    }
  };

  // Make showReviewForm global
  window.showReviewForm = function (placeDataInput) {
    console.log(
      "Global showReviewForm called with input type:",
      typeof placeDataInput,
      "Value:",
      placeDataInput
    );

    let placeData;
    if (typeof placeDataInput === "string") {
      try {
        placeData = JSON.parse(placeDataInput);
        console.log("Parsed string input successfully.");
      } catch (e) {
        console.error(
          "Error parsing string input in showReviewForm:",
          e,
          "Input:",
          placeDataInput
        );
        alert(
          "Internal error: Cannot prepare review form (Invalid Data String)."
        );
        return;
      }
    } else if (typeof placeDataInput === "object" && placeDataInput !== null) {
      placeData = placeDataInput;
      console.log("Input is already an object.");
    } else {
      console.error(
        "Invalid input type for showReviewForm. Expected object or JSON string, received:",
        placeDataInput
      );
      alert("Internal error: Cannot prepare review form (Invalid Data Type).");
      return;
    }

    const requiredReviewElements = [
      reviewImageSection,
      reviewImageForm,
      reviewFormTitle,
      reviewTitleInput,
      reviewTextInput,
      reviewImageInput,
      reviewSubmitBtn,
    ];
    if (requiredReviewElements.some((el) => !el)) {
      console.error(
        "CRITICAL: One or more Review Form elements missing!",
        requiredReviewElements
      );
      alert("Error: Essential review form elements are missing.");
      return;
    }
    console.log("Review Form elements seem to exist in DOM.");

    try {
      if (!placeData || !placeData.id) {
        throw new Error(
          "placeData object is invalid or missing ID after processing."
        );
      }

      if (reviewFormTitle)
        reviewFormTitle.textContent = placeData.name || "Unknown";
      if (reviewTitleInput)
        reviewTitleInput.value = placeData.review_title || "";
      if (reviewTextInput) reviewTextInput.value = placeData.review || "";
      if (reviewImageInput) reviewImageInput.value = ""; // Clear file input
      if (reviewSubmitBtn) {
        reviewSubmitBtn.disabled = false;
        reviewSubmitBtn.textContent = "Save Review & Image";
      }

      // Construct URL - Ensure endpoint name is correct
      const reviewUrl = `/places/${placeData.id}/review-image`;
      if (reviewImageForm) reviewImageForm.action = reviewUrl;
      console.log("Review form action set to:", reviewUrl);

      hideAllForms(); // Hide other forms
      if (reviewImageSection) {
        reviewImageSection.style.display = "block";
        console.log("Review form displayed.");
        reviewImageSection.scrollIntoView({
          behavior: "smooth",
          block: "start",
        });
      }
    } catch (e) {
      console.error("Error populating review form fields:", e);
      console.log("State of placeData during error:", placeData);
      alert("Internal error: Cannot populate review form.");
    }
  };

  window.hideReviewForm = function () {
    if (reviewImageSection) reviewImageSection.style.display = "none";
    // Optionally show the main toggle button if nothing else is active
    if (
      addPlaceWrapper &&
      addPlaceWrapper.style.display === "none" &&
      editPlaceSection &&
      editPlaceSection.style.display === "none" &&
      seeReviewSection &&
      seeReviewSection.style.display === "none"
    ) {
      if (toggleAddPlaceBtn) toggleAddPlaceBtn.textContent = "Add New Place";
    }
  };

  // Make showSeeReviewModal global
  window.showSeeReviewModal = function (placeDataJSONString) {
    console.log("Global showSeeReviewModal called.");
    let placeData;
    try {
      placeData = JSON.parse(placeDataJSONString);
      if (seeReviewEditBtn) {
        seeReviewEditBtn.setAttribute("data-place-json", placeDataJSONString); // Store the STRING
      } else {
        console.error("Could not find seeReviewEditBtn to store data.");
      }
    } catch (e) {
      console.error(
        "Error parsing placeData JSON for see review:",
        e,
        "String:",
        placeDataJSONString
      );
      alert("Error reading place data for review display.");
      if (seeReviewEditBtn) seeReviewEditBtn.removeAttribute("data-place-json");
      return;
    }

    const requiredSeeReviewElements = [
      seeReviewSection,
      seeReviewPlaceTitle,
      seeReviewDisplayTitle,
      seeReviewDisplayText,
      seeReviewDisplayImage,
      seeReviewEditBtn,
    ];
    if (requiredSeeReviewElements.some((el) => !el)) {
      console.error(
        "CRITICAL: One or more See Review modal elements missing!",
        requiredSeeReviewElements
      );
      alert("Error: Review display elements are missing.");
      return;
    }

    try {
      seeReviewPlaceTitle.textContent = placeData.name || "Unknown Place";
      seeReviewDisplayTitle.textContent = placeData.review_title || "";
      seeReviewDisplayText.textContent =
        placeData.review ||
        (placeData.review_title ? "" : "(No review text entered)");
      seeReviewDisplayTitle.style.display = placeData.review_title
        ? "block"
        : "none";

      if (placeData.image_url && placeData.image_url.startsWith("http")) {
        seeReviewDisplayImage.src = placeData.image_url;
        seeReviewDisplayImage.alt = `Image for ${placeData.name || "place"}`;
        seeReviewDisplayImage.style.display = "block";
      } else {
        seeReviewDisplayImage.style.display = "none";
        seeReviewDisplayImage.src = "";
      }

      hideAllForms(); // Hide other forms
      seeReviewSection.style.display = "block";
      seeReviewSection.scrollIntoView({ behavior: "smooth", block: "start" });
    } catch (e) {
      console.error("Error populating see review modal:", e);
      alert("Error preparing review display.");
    }
  };

  window.hideSeeReviewModal = function () {
    if (seeReviewSection) seeReviewSection.style.display = "none";
    if (seeReviewEditBtn) seeReviewEditBtn.removeAttribute("data-place-json"); // Clear data when hiding
    console.log("See Review modal hidden.");
    // Optionally show the main toggle button if nothing else is active
    if (
      addPlaceWrapper &&
      addPlaceWrapper.style.display === "none" &&
      editPlaceSection &&
      editPlaceSection.style.display === "none" &&
      reviewImageSection &&
      reviewImageSection.style.display === "none"
    ) {
      if (toggleAddPlaceBtn) toggleAddPlaceBtn.textContent = "Add New Place";
    }
  };

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

  if (addPlaceForm) {
    addPlaceForm.addEventListener("submit", (event) => {
      if (!hiddenLat || !hiddenLon || !hiddenLat.value || !hiddenLon.value) {
        event.preventDefault();
        setStatusMessage(
          geocodeStatus,
          'Coordinates missing. Use "Find" button first.',
          "error"
        );
        if (addSubmitBtn) addSubmitBtn.disabled = false; // Re-enable if validation fails
        return false;
      }
      if (addSubmitBtn) {
        addSubmitBtn.disabled = true;
        addSubmitBtn.textContent = "Adding...";
      }
      // Form submission will cause page reload, no need to explicitly hide form here
    });
  }

  if (editFindCoordsBtn) {
    editFindCoordsBtn.addEventListener("click", () => findCoordinates("edit"));
  }

  if (editPlaceForm) {
    // Attach listener to the form itself for cancel button inside it
    editPlaceForm.addEventListener("click", function (event) {
      if (event.target && event.target.matches("button.cancel-btn")) {
        hideEditPlaceForm();
      }
    });
    editPlaceForm.addEventListener("submit", (event) => {
      if (
        !editLatitudeInput ||
        !editLongitudeInput ||
        !editLatitudeInput.value ||
        !editLongitudeInput.value
      ) {
        event.preventDefault();
        setStatusMessage(
          editGeocodeStatus,
          "Coordinates missing or invalid.",
          "error"
        );
        if (editSubmitBtn) editSubmitBtn.disabled = false; // Re-enable on validation fail
        return false;
      }
      if (editSubmitBtn) {
        editSubmitBtn.disabled = true;
        editSubmitBtn.textContent = "Saving...";
      }
    });
  }

  if (reviewImageForm) {
    // Attach listener to the form itself for cancel button inside it
    reviewImageForm.addEventListener("click", function (event) {
      if (event.target && event.target.matches("button.cancel-btn")) {
        hideReviewForm();
      }
    });
    reviewImageForm.addEventListener("submit", (event) => {
      if (reviewSubmitBtn) {
        reviewSubmitBtn.disabled = true;
        reviewSubmitBtn.textContent = "Saving...";
      }
    });
  }

  if (seeReviewSection) {
    // Attach listener to the section for cancel button inside it
    seeReviewSection.addEventListener("click", function (event) {
      if (event.target && event.target.matches("button.cancel-btn")) {
        hideSeeReviewModal();
      }
    });
  }

  if (seeReviewEditBtn) {
    seeReviewEditBtn.addEventListener("click", (event) => {
      console.log("Edit Review button clicked from See Review modal.");
      const button = event.target;
      const placeDataJSONString = button.getAttribute("data-place-json");

      if (placeDataJSONString) {
        try {
          const placeDataObject = JSON.parse(placeDataJSONString); // Parse here
          console.log("Parsed data for edit:", placeDataObject);
          // hideSeeReviewModal(); // showReviewForm will hide it
          window.showReviewForm(placeDataObject); // Pass the OBJECT
        } catch (e) {
          console.error(
            "Error parsing placeData JSON from button attribute:",
            e,
            "String:",
            placeDataJSONString
          );
          alert("Error reading data needed to edit review.");
        }
      } else {
        console.error(
          "Cannot edit review, data attribute 'data-place-json' is missing or empty on the button."
        );
        alert(
          "Error: Could not retrieve data to edit review (attribute missing)."
        );
      }
    });
  }

  // Initial state setup
  hideAllForms();
  if (addSubmitBtn) addSubmitBtn.disabled = true; // Initially disable Add Place submit

  console.log("JS Initialization Complete. Event listeners attached.");
}); // End of DOMContentLoaded listener
