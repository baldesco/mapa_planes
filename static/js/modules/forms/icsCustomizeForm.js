/**
 * icsCustomizeForm.js
 * Manages the modal and form for customizing .ics calendar event details,
 * and generating direct links for Google & Outlook calendars.
 */
import apiClient from "../apiClient.js";
import { setStatusMessage } from "../components/statusMessages.js";

const icsCustomizeForm = {
  elements: {
    modal: null,
    form: null,
    visitTitleSpan: null,
    visitIdInput: null,
    eventNameInput: null,
    durationValueInput: null,
    durationUnitSelect: null,
    remind1DayCheckbox: null,
    remind2HoursCheckbox: null,
    remind15MinsCheckbox: null,
    statusMessage: null,
    instructionMessageDiv: null,
    downloadBtn: null,
    googleCalendarBtn: null,
    outlookCalendarBtn: null,
    cancelBtn: null,
  },
  currentVisitData: null,
  currentPlaceData: null,
  hideCallback: null,

  init(hideFn) {
    this.hideCallback = hideFn;
    this.cacheDOMElements();
    this.setupEventListeners();
  },

  cacheDOMElements() {
    this.elements.modal = document.getElementById("ics-customize-modal");
    if (!this.elements.modal) {
      console.error(
        "ICS Customize Modal: Element #ics-customize-modal not found."
      );
      return;
    }
    this.elements.form = document.getElementById("ics-customize-form");
    this.elements.visitTitleSpan = document.getElementById(
      "ics-modal-visit-title"
    );
    this.elements.visitIdInput = document.getElementById("ics-visit-id");
    this.elements.eventNameInput = document.getElementById("ics-event-name");
    this.elements.durationValueInput =
      document.getElementById("ics-duration-value");
    this.elements.durationUnitSelect =
      document.getElementById("ics-duration-unit");
    this.elements.remind1DayCheckbox =
      document.getElementById("ics-remind-1-day");
    this.elements.remind2HoursCheckbox =
      document.getElementById("ics-remind-2-hours");
    this.elements.remind15MinsCheckbox =
      document.getElementById("ics-remind-15-mins");
    this.elements.statusMessage = document.getElementById(
      "ics-customize-status"
    );
    this.elements.instructionMessageDiv =
      document.getElementById("ics-instructions");
    this.elements.downloadBtn = document.getElementById("ics-download-btn");
    this.elements.googleCalendarBtn = document.getElementById(
      "ics-google-calendar-btn"
    );
    this.elements.outlookCalendarBtn = document.getElementById(
      "ics-outlook-calendar-btn"
    );
    this.elements.cancelBtn = document.getElementById(
      "ics-customize-cancel-btn"
    );
  },

  setupEventListeners() {
    if (!this.elements.modal) return;

    if (this.elements.downloadBtn) {
      this.elements.downloadBtn.addEventListener("click", () =>
        this.handleDownloadIcs()
      );
    }
    if (this.elements.googleCalendarBtn) {
      this.elements.googleCalendarBtn.addEventListener("click", () =>
        this.handleAddToGoogleCalendar()
      );
    }
    if (this.elements.outlookCalendarBtn) {
      this.elements.outlookCalendarBtn.addEventListener("click", () =>
        this.handleAddToOutlookCalendar()
      );
    }

    if (this.elements.cancelBtn && this.hideCallback) {
      this.elements.cancelBtn.addEventListener("click", () => {
        if (this.elements.instructionMessageDiv)
          this.elements.instructionMessageDiv.style.display = "none";
        this.hideCallback();
      });
    }
  },

  populateForm(visitData, placeData) {
    if (
      !this.elements.form ||
      !visitData ||
      !visitData.id ||
      !placeData ||
      !placeData.id
    ) {
      console.error(
        "ICS Customize Modal: Cannot populate - missing form or essential data."
      );
      return false;
    }
    this.currentVisitData = visitData;
    this.currentPlaceData = placeData;

    this.elements.form.reset();
    setStatusMessage(this.elements.statusMessage, "", "info");
    if (this.elements.instructionMessageDiv)
      this.elements.instructionMessageDiv.style.display = "none";

    if (this.elements.visitTitleSpan) {
      const visitDate = new Date(visitData.visit_datetime);
      const formattedDate = visitDate.toLocaleDateString(undefined, {
        month: "short",
        day: "numeric",
      });
      this.elements.visitTitleSpan.textContent = `"${
        placeData.name || "Event"
      }" on ${formattedDate}`;
    }
    if (this.elements.visitIdInput)
      this.elements.visitIdInput.value = visitData.id;
    if (this.elements.eventNameInput)
      this.elements.eventNameInput.value = `Visit: ${
        placeData.name || "Selected Place"
      }`;
    if (this.elements.durationValueInput)
      this.elements.durationValueInput.value = "2"; // Default duration
    if (this.elements.durationUnitSelect)
      this.elements.durationUnitSelect.value = "hours"; // Default unit

    if (this.elements.remind1DayCheckbox)
      this.elements.remind1DayCheckbox.checked = true;
    if (this.elements.remind2HoursCheckbox)
      this.elements.remind2HoursCheckbox.checked = true;
    if (this.elements.remind15MinsCheckbox)
      this.elements.remind15MinsCheckbox.checked = true;

    [
      this.elements.downloadBtn,
      this.elements.googleCalendarBtn,
      this.elements.outlookCalendarBtn,
    ].forEach((btn) => {
      if (btn) btn.disabled = false;
    });
    return true;
  },

  _getEventDetailsFromForm() {
    const eventName = this.elements.eventNameInput.value;
    const durationValue = parseInt(this.elements.durationValueInput.value);
    const durationUnit = this.elements.durationUnitSelect.value;
    const place = this.currentPlaceData;
    const visit = this.currentVisitData;

    const startDateTime = new Date(visit.visit_datetime);
    let endDateTime = new Date(startDateTime.getTime());

    if (durationUnit === "minutes") {
      endDateTime.setUTCMinutes(startDateTime.getUTCMinutes() + durationValue);
    } else if (durationUnit === "hours") {
      endDateTime.setUTCHours(startDateTime.getUTCHours() + durationValue);
    } else if (durationUnit === "days") {
      endDateTime.setUTCDate(startDateTime.getUTCDate() + durationValue);
    }

    let description = `Visit to ${place.name || "the selected place"}.`;
    if (visit.review_title) {
      description += `\nNote: ${visit.review_title}`;
    }

    if (place.latitude != null && place.longitude != null) {
      const mapsUrl = `https://www.google.com/maps?q=${place.latitude},${place.longitude}`;
      description += `\n\nView on Map: ${mapsUrl}`;
    }
    // Example deep link back to your app (if you implement such routes)
    // description += `\n\nView in Mapa Planes: ${window.location.origin}/places/${place.id}/visits/${visit.id}`;

    let locationString = "";
    const addressParts = [];

    // Try to use a comprehensive display_name if available
    if (place.display_name && place.display_name.length > 5) {
      // A simple check to see if display_name might be better than constructing it
      const nameInDisplay = place.name
        ? place.display_name.includes(place.name)
        : false;
      const addressInDisplay = place.address
        ? place.display_name.includes(place.address)
        : false;
      if (nameInDisplay || addressInDisplay) {
        locationString = place.display_name;
      }
    }

    // If display_name wasn't suitable, construct from parts
    if (!locationString) {
      if (place.name) addressParts.push(place.name);
      // Avoid duplicating name if it's likely part of the address
      if (
        place.address &&
        (!place.name || !place.address.includes(place.name))
      ) {
        addressParts.push(place.address);
      }
      if (place.city) addressParts.push(place.city);
      if (place.country) addressParts.push(place.country);
      locationString = addressParts.filter(Boolean).join(", "); // Filter out empty parts
    }

    // Fallback to coordinates for the location parameter if the address string is still weak
    if (
      (!locationString || locationString.length < 5) &&
      place.latitude != null &&
      place.longitude != null
    ) {
      locationString = `${place.latitude},${place.longitude}`;
    }

    return {
      name: eventName,
      startUTC: startDateTime,
      endUTC: endDateTime,
      description: description,
      location: locationString,
      timezone: place.timezone_iana || "UTC",
    };
  },

  _formatDateForGoogle(date) {
    // Expects UTC Date object
    return date.toISOString().replace(/-|:|\.\d{3}/g, "");
  },

  _formatDateForOutlook(date) {
    // Expects UTC Date object
    const pad = (num) => (num < 10 ? "0" + num : num);
    return `${date.getUTCFullYear()}-${pad(date.getUTCMonth() + 1)}-${pad(
      date.getUTCDate()
    )}T${pad(date.getUTCHours())}:${pad(date.getUTCMinutes())}:${pad(
      date.getUTCSeconds()
    )}`;
  },

  handleAddToGoogleCalendar() {
    if (!this.currentVisitData || !this.currentPlaceData) {
      setStatusMessage(
        this.elements.statusMessage,
        "Error: Missing visit or place data.",
        "error"
      );
      return;
    }
    setStatusMessage(this.elements.statusMessage, "", "info");
    if (this.elements.instructionMessageDiv)
      this.elements.instructionMessageDiv.style.display = "none";

    const eventDetails = this._getEventDetailsFromForm();
    if (!eventDetails.name || !eventDetails.startUTC || !eventDetails.endUTC) {
      setStatusMessage(
        this.elements.statusMessage,
        "Please fill in event name and ensure dates are valid.",
        "error"
      );
      return;
    }

    const googleUrl = new URL("https://www.google.com/calendar/render");
    googleUrl.searchParams.set("action", "TEMPLATE");
    googleUrl.searchParams.set("text", eventDetails.name);
    googleUrl.searchParams.set(
      "dates",
      `${this._formatDateForGoogle(
        eventDetails.startUTC
      )}/${this._formatDateForGoogle(eventDetails.endUTC)}`
    );
    googleUrl.searchParams.set("details", eventDetails.description);
    if (eventDetails.location) {
      googleUrl.searchParams.set("location", eventDetails.location);
    }
    googleUrl.searchParams.set("ctz", eventDetails.timezone); // Let Google handle display in user's chosen timezone

    window.open(googleUrl.toString(), "_blank");
  },

  handleAddToOutlookCalendar() {
    if (!this.currentVisitData || !this.currentPlaceData) {
      setStatusMessage(
        this.elements.statusMessage,
        "Error: Missing visit or place data.",
        "error"
      );
      return;
    }
    setStatusMessage(this.elements.statusMessage, "", "info");
    if (this.elements.instructionMessageDiv)
      this.elements.instructionMessageDiv.style.display = "none";

    const eventDetails = this._getEventDetailsFromForm();
    if (!eventDetails.name || !eventDetails.startUTC || !eventDetails.endUTC) {
      setStatusMessage(
        this.elements.statusMessage,
        "Please fill in event name and ensure dates are valid.",
        "error"
      );
      return;
    }

    const outlookUrl = new URL(
      "https://outlook.live.com/calendar/0/deeplink/compose"
    );
    outlookUrl.searchParams.set("path", "/calendar/action/compose");
    outlookUrl.searchParams.set("rru", "addevent");
    outlookUrl.searchParams.set("subject", eventDetails.name);
    // Send UTC times, Outlook will display them in the user's configured timezone.
    outlookUrl.searchParams.set(
      "startdt",
      this._formatDateForOutlook(eventDetails.startUTC) + "Z"
    );
    outlookUrl.searchParams.set(
      "enddt",
      this._formatDateForOutlook(eventDetails.endUTC) + "Z"
    );
    outlookUrl.searchParams.set("body", eventDetails.description);
    if (eventDetails.location) {
      outlookUrl.searchParams.set("location", eventDetails.location);
    }

    window.open(outlookUrl.toString(), "_blank");
  },

  async handleDownloadIcs() {
    if (
      !this.elements.form ||
      !this.currentVisitData ||
      !this.currentVisitData.id
    ) {
      setStatusMessage(
        this.elements.statusMessage,
        "Error: Missing visit information for .ics download.",
        "error"
      );
      if (this.elements.instructionMessageDiv)
        this.elements.instructionMessageDiv.style.display = "none";
      return;
    }

    setStatusMessage(
      this.elements.statusMessage,
      "Generating calendar file...",
      "loading"
    );
    if (this.elements.instructionMessageDiv)
      this.elements.instructionMessageDiv.style.display = "none";
    [
      this.elements.downloadBtn,
      this.elements.googleCalendarBtn,
      this.elements.outlookCalendarBtn,
    ].forEach((btn) => {
      if (btn) btn.disabled = true;
    });

    const visitId = this.currentVisitData.id;
    const payload = {
      event_name: this.elements.eventNameInput.value,
      duration_value: parseInt(this.elements.durationValueInput.value),
      duration_unit: this.elements.durationUnitSelect.value,
      remind_1_day_before: this.elements.remind1DayCheckbox.checked,
      remind_2_hours_before: this.elements.remind2HoursCheckbox.checked,
      remind_15_mins_before: this.elements.remind15MinsCheckbox.checked,
    };

    try {
      const apiUrl = `/api/v1/visits/${visitId}/calendar_event`;
      const response = await apiClient.post(apiUrl, payload);

      if (response.ok) {
        const blob = await response.blob();
        const contentDisposition = response.headers.get("content-disposition");
        let filename = "visit.ics";
        if (contentDisposition) {
          // More robust filename extraction from Content-Disposition
          const filenameMatch = contentDisposition.match(
            /filename\*?=(?:UTF-8'')?([^;\r\n]+)|filename="?([^"]+)"?/i
          );
          if (filenameMatch) {
            // Prefer the second group if quoted, otherwise the first (for filename*=UTF-8''...)
            // Decode URI component for cases like filename*=UTF-8''%e2%82%ac%20event.ics
            filename = decodeURIComponent(
              filenameMatch[1] || filenameMatch[2]
            ).replace(/^"|"$/g, "");
          }
        }

        const url = window.URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.style.display = "none";
        a.href = url;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        a.remove();
        window.URL.revokeObjectURL(url);

        setStatusMessage(this.elements.statusMessage, "", "info");
        if (this.elements.instructionMessageDiv) {
          this.elements.instructionMessageDiv.innerHTML = `
                    <p style="margin-bottom: 5px;"><strong>'${filename}' downloaded!</strong></p>
                    <p style="font-size:0.9em; margin-bottom: 5px;">To add to your calendar:</p>
                    <ul style="font-size:0.85em; margin:0; padding-left: 20px; text-align: left;">
                        <li><strong>Desktop:</strong> Double-click the .ics file or use Import.</li>
                        <li><strong>Google Calendar:</strong> Settings (⚙️) > Import & export.</li>
                        <li><strong>Outlook.com:</strong> Add calendar > Upload from file.</li>
                        <li><strong>Mobile:</strong> Tap the downloaded file.</li>
                    </ul>`;
          this.elements.instructionMessageDiv.style.display = "block";
        } else {
          alert("Calendar file downloaded!");
        }
      } else {
        const result = await response
          .json()
          .catch(() => ({ detail: "Failed to generate calendar file." }));
        setStatusMessage(this.elements.statusMessage, result.detail, "error");
      }
    } catch (error) {
      console.error("Error generating calendar file:", error);
      setStatusMessage(
        this.elements.statusMessage,
        "An error occurred. Please try again.",
        "error"
      );
    } finally {
      [
        this.elements.downloadBtn,
        this.elements.googleCalendarBtn,
        this.elements.outlookCalendarBtn,
      ].forEach((btn) => {
        if (btn) btn.disabled = false;
      });
    }
  },
};
export default icsCustomizeForm;
