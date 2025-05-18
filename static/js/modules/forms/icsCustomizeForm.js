/**
 * icsCustomizeForm.js
 * Manages the modal and form for customizing .ics calendar event details.
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
    this.elements.cancelBtn = document.getElementById(
      "ics-customize-cancel-btn"
    );
  },

  setupEventListeners() {
    if (!this.elements.form) return;
    this.elements.form.addEventListener("submit", (event) =>
      this.handleSubmit(event)
    );
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
      this.elements.visitTitleSpan.textContent = `"${placeData.name}" on ${formattedDate}`;
    }
    if (this.elements.visitIdInput)
      this.elements.visitIdInput.value = visitData.id;
    if (this.elements.eventNameInput)
      this.elements.eventNameInput.value = `Visit: ${placeData.name}`;
    if (this.elements.durationValueInput)
      this.elements.durationValueInput.value = "1";
    if (this.elements.durationUnitSelect)
      this.elements.durationUnitSelect.value = "hours";

    if (this.elements.remind1DayCheckbox)
      this.elements.remind1DayCheckbox.checked = true;
    if (this.elements.remind2HoursCheckbox)
      this.elements.remind2HoursCheckbox.checked = true;
    if (this.elements.remind15MinsCheckbox)
      this.elements.remind15MinsCheckbox.checked = true;

    if (this.elements.downloadBtn) this.elements.downloadBtn.disabled = false;
    return true;
  },

  async handleSubmit(event) {
    event.preventDefault();
    if (
      !this.elements.form ||
      !this.currentVisitData ||
      !this.currentVisitData.id
    ) {
      setStatusMessage(
        this.elements.statusMessage,
        "Error: Missing visit information.",
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
    if (this.elements.downloadBtn) this.elements.downloadBtn.disabled = true;

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
          const filenameMatch = contentDisposition.match(/filename="?(.+)"?/i);
          if (filenameMatch && filenameMatch.length === 2)
            filename = filenameMatch[1];
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
          alert(
            "Calendar file downloaded!\n\nTo add to your calendar:\n- Desktop: Double-click the .ics file or use Import.\n- Google Calendar: Settings > Import & export.\n- Outlook.com: Add calendar > Upload from file.\n- Mobile: Tap the downloaded file."
          );
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
      if (this.elements.downloadBtn) this.elements.downloadBtn.disabled = false;
    }
  },
};
export default icsCustomizeForm;
