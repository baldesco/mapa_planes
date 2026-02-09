/**
 * icsCustomizeForm.js
 * Manages the export of visits to external calendar applications.
 * Integrated with the SPA-lite overlay system.
 */
import apiClient from "../apiClient.js";
import { setStatusMessage } from "../components/statusMessages.js";

const icsCustomizeForm = {
  elements: {
    modal: null,
    form: null,
    visitIdInput: null,
    eventNameInput: null,
    durationValueInput: null,
    durationUnitSelect: null,
    statusMessage: null,
    downloadBtn: null,
    googleBtn: null,
    cancelBtn: null,
  },
  currentVisit: null,
  currentPlace: null,
  hideCallback: null,

  init(hideFn) {
    this.hideCallback = hideFn;
    this.cacheDOMElements();
    this.setupEventListeners();
  },

  cacheDOMElements() {
    this.elements.modal = document.getElementById("ics-customize-modal");
    if (!this.elements.modal) return;

    this.elements.form = document.getElementById("ics-customize-form");
    this.elements.visitIdInput = document.getElementById("ics-visit-id");
    this.elements.eventNameInput = document.getElementById("ics-event-name");
    this.elements.durationValueInput =
      document.getElementById("ics-duration-value");
    this.elements.durationUnitSelect =
      document.getElementById("ics-duration-unit");
    this.elements.statusMessage = document.getElementById(
      "ics-customize-status",
    );
    this.elements.downloadBtn = document.getElementById("ics-download-btn");
    this.elements.googleBtn = document.getElementById(
      "ics-google-calendar-btn",
    );
    this.elements.cancelBtn = this.elements.modal.querySelector(".cancel-btn");
  },

  setupEventListeners() {
    if (!this.elements.form) return;

    this.elements.downloadBtn?.addEventListener("click", () =>
      this.handleDownload(),
    );
    this.elements.googleBtn?.addEventListener("click", () =>
      this.handleGoogleCalendar(),
    );

    if (this.elements.cancelBtn && this.hideCallback) {
      this.elements.cancelBtn.addEventListener("click", () =>
        this.hideCallback(),
      );
    }
  },

  populateForm(visitData, placeData) {
    if (!visitData || !placeData) return false;

    this.currentVisit = visitData;
    this.currentPlace = placeData;

    this.elements.form.reset();
    setStatusMessage(this.elements.statusMessage, "");

    this.elements.visitIdInput.value = visitData.id;
    this.elements.eventNameInput.value = `Visit: ${placeData.name}`;

    return true;
  },

  getEventParams() {
    const start = new Date(this.currentVisit.visit_datetime);
    const duration = parseInt(this.elements.durationValueInput.value);
    const unit = this.elements.durationUnitSelect.value;

    const end = new Date(start);
    if (unit === "hours") end.setHours(start.getHours() + duration);
    else end.setMinutes(start.getMinutes() + duration);

    return {
      title: this.elements.eventNameInput.value,
      start: start,
      end: end,
      location: this.currentPlace.address || this.currentPlace.name,
      description: `Planned visit to ${this.currentPlace.name}. Recorded in Mapa Planes.`,
    };
  },

  async handleDownload() {
    setStatusMessage(
      this.elements.statusMessage,
      "Generating file...",
      "loading",
    );

    const payload = {
      event_name: this.elements.eventNameInput.value,
      duration_value: parseInt(this.elements.durationValueInput.value),
      duration_unit: this.elements.durationUnitSelect.value,
      remind_1_day_before: true,
      remind_2_hours_before: true,
      remind_15_mins_before: false,
    };

    try {
      const response = await apiClient.post(
        `/api/v1/visits/${this.currentVisit.id}/calendar_event`,
        payload,
      );
      if (response.ok) {
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = `visit-${this.currentVisit.id}.ics`;
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        a.remove();
        setStatusMessage(this.elements.statusMessage, "Downloaded!", "success");
      } else {
        setStatusMessage(
          this.elements.statusMessage,
          "Export failed.",
          "error",
        );
      }
    } catch (error) {
      setStatusMessage(this.elements.statusMessage, "Network error.", "error");
    }
  },

  handleGoogleCalendar() {
    const params = this.getEventParams();
    const fmt = (d) => d.toISOString().replace(/-|:|\.\d\d\d/g, "");

    const url = new URL(
      "https://calendar.google.com/calendar/render?action=TEMPLATE",
    );
    url.searchParams.set("text", params.title);
    url.searchParams.set("dates", `${fmt(params.start)}/${fmt(params.end)}`);
    url.searchParams.set("details", params.description);
    url.searchParams.set("location", params.location);

    window.open(url.toString(), "_blank");
  },
};

export default icsCustomizeForm;
