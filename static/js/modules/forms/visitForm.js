/**
 * visitForm.js
 * Manages interactions and state for the Plan/Edit Visit form.
 */
import apiClient from "../apiClient.js";
import { setStatusMessage } from "../components/statusMessages.js";

const visitForm = {
  elements: {
    wrapper: null,
    form: null,
    formTitle: null,
    placeTitleSpan: null,
    placeIdInput: null,
    visitIdInput: null,
    dateInput: null,
    timeInput: null,
    reminderEnabledCheckbox: null,
    reminderOptionsDiv: null,
    reminderOffsetCheckboxes: [],
    statusMessage: null,
    submitBtn: null,
    cancelBtn: null,
  },
  currentPlaceData: null,
  currentVisitData: null,
  hideCallback: null,
  onVisitSavedCallback: null,

  init(hideFn, onSaveFn) {
    this.hideCallback = hideFn;
    this.onVisitSavedCallback = onSaveFn;
    this.cacheDOMElements();
    this.setupEventListeners();
  },

  cacheDOMElements() {
    this.elements.wrapper = document.getElementById("plan-visit-section");
    if (!this.elements.wrapper) {
      console.error(
        "Visit Form: Wrapper element #plan-visit-section not found."
      );
      return;
    }
    this.elements.form = document.getElementById("plan-visit-form");
    this.elements.formTitle = this.elements.wrapper.querySelector("h2");
    this.elements.placeTitleSpan = document.getElementById(
      "plan-visit-place-title"
    );
    this.elements.placeIdInput = document.getElementById("plan-visit-place-id");
    this.elements.visitIdInput = document.getElementById("plan-visit-id");
    this.elements.dateInput = document.getElementById("visit-date");
    this.elements.timeInput = document.getElementById("visit-time");
    this.elements.reminderEnabledCheckbox = document.getElementById(
      "visit-reminder-enabled"
    );
    this.elements.reminderOptionsDiv = document.getElementById(
      "visit-reminder-options"
    );
    this.elements.reminderOffsetCheckboxes = Array.from(
      this.elements.reminderOptionsDiv?.querySelectorAll(
        'input[name="reminder_offsets"]'
      ) || []
    );
    this.elements.statusMessage = document.getElementById("plan-visit-status");
    this.elements.submitBtn = document.getElementById("plan-visit-submit-btn");
    this.elements.cancelBtn = document.getElementById("plan-visit-cancel-btn");
  },

  setupEventListeners() {
    if (!this.elements.form) return;
    this.elements.form.addEventListener("submit", (event) =>
      this.handleSubmit(event)
    );
    if (this.elements.cancelBtn && this.hideCallback) {
      this.elements.cancelBtn.addEventListener("click", () =>
        this.hideCallback()
      );
    }
    if (
      this.elements.reminderEnabledCheckbox &&
      this.elements.reminderOptionsDiv
    ) {
      this.elements.reminderEnabledCheckbox.addEventListener(
        "change",
        (event) => {
          this.elements.reminderOptionsDiv.style.display = event.target.checked
            ? "block"
            : "none";
        }
      );
    }
  },

  populateForm(placeData, visitData = null) {
    if (!this.elements.form || !placeData || !placeData.id) {
      console.error(
        "Visit Form: Cannot populate - missing form or valid placeData."
      );
      return false;
    }
    this.currentPlaceData = placeData;
    this.currentVisitData = visitData;

    this.elements.form.reset();
    if (this.elements.reminderOptionsDiv)
      this.elements.reminderOptionsDiv.style.display = "none";
    setStatusMessage(this.elements.statusMessage, "", "info");

    if (this.elements.placeTitleSpan)
      this.elements.placeTitleSpan.textContent = `"${
        placeData.name || "Unknown Place"
      }"`;
    if (this.elements.placeIdInput)
      this.elements.placeIdInput.value = placeData.id;

    if (visitData) {
      if (this.elements.formTitle)
        this.elements.formTitle.textContent = "Edit Visit for:";
      if (this.elements.visitIdInput)
        this.elements.visitIdInput.value = visitData.id;
      if (this.elements.submitBtn)
        this.elements.submitBtn.textContent = "Save Changes";

      if (this.elements.dateInput && visitData.visit_datetime) {
        this.elements.dateInput.value = new Date(visitData.visit_datetime)
          .toISOString()
          .split("T")[0];
      }
      if (this.elements.timeInput && visitData.visit_datetime) {
        const timeStr = new Date(visitData.visit_datetime)
          .toTimeString()
          .split(" ")[0];
        this.elements.timeInput.value = timeStr.substring(0, 5);
      }
      if (this.elements.reminderEnabledCheckbox) {
        this.elements.reminderEnabledCheckbox.checked =
          visitData.reminder_enabled || false;
        if (this.elements.reminderOptionsDiv)
          this.elements.reminderOptionsDiv.style.display =
            visitData.reminder_enabled ? "block" : "none";
      }
      if (
        this.elements.reminderOffsetCheckboxes.length > 0 &&
        visitData.reminder_offsets_hours
      ) {
        this.elements.reminderOffsetCheckboxes.forEach((cb) => {
          cb.checked = visitData.reminder_offsets_hours.includes(
            parseInt(cb.value)
          );
        });
      }
    } else {
      if (this.elements.formTitle)
        this.elements.formTitle.textContent = "Plan New Visit for:";
      if (this.elements.visitIdInput) this.elements.visitIdInput.value = "";
      if (this.elements.submitBtn)
        this.elements.submitBtn.textContent = "Schedule Visit";
      const now = new Date();
      now.setHours(now.getHours() + 1);
      now.setMinutes(0);
      if (this.elements.dateInput)
        this.elements.dateInput.value = now.toISOString().split("T")[0];
      if (this.elements.timeInput)
        this.elements.timeInput.value = now.toTimeString().substring(0, 5);
    }
    if (this.elements.submitBtn) this.elements.submitBtn.disabled = false;
    return true;
  },

  async handleSubmit(event) {
    event.preventDefault();
    if (
      !this.elements.form ||
      !this.currentPlaceData ||
      !this.currentPlaceData.id
    ) {
      setStatusMessage(
        this.elements.statusMessage,
        "Error: Missing place information for the visit.",
        "error"
      );
      return;
    }

    setStatusMessage(this.elements.statusMessage, "Saving visit...", "loading");
    if (this.elements.submitBtn) this.elements.submitBtn.disabled = true;

    const formData = new FormData(this.elements.form);
    const placeId = this.currentPlaceData.id;
    const visitId = this.currentVisitData ? this.currentVisitData.id : null;
    const dateValue = this.elements.dateInput.value;
    const timeValue = this.elements.timeInput.value;

    if (!dateValue || !timeValue) {
      setStatusMessage(
        this.elements.statusMessage,
        "Date and Time are required.",
        "error"
      );
      if (this.elements.submitBtn) this.elements.submitBtn.disabled = false;
      return;
    }
    const localDateTime = new Date(`${dateValue}T${timeValue}:00`);
    if (isNaN(localDateTime.getTime())) {
      setStatusMessage(
        this.elements.statusMessage,
        "Invalid Date or Time.",
        "error"
      );
      if (this.elements.submitBtn) this.elements.submitBtn.disabled = false;
      return;
    }
    const visit_datetime_iso = localDateTime.toISOString();
    // console.log("VisitForm: Scheduling visit with visit_datetime (ISO UTC):", visit_datetime_iso); // Keep for debugging if status issue persists

    const reminderEnabled = this.elements.reminderEnabledCheckbox
      ? this.elements.reminderEnabledCheckbox.checked
      : false;
    let reminderOffsets = [];
    if (reminderEnabled && this.elements.reminderOffsetCheckboxes.length > 0) {
      this.elements.reminderOffsetCheckboxes.forEach((cb) => {
        if (cb.checked) reminderOffsets.push(parseInt(cb.value));
      });
    }

    const payload = {
      place_id: parseInt(placeId),
      visit_datetime: visit_datetime_iso,
      reminder_enabled: reminderEnabled,
      reminder_offsets_hours:
        reminderOffsets.length > 0 ? reminderOffsets : null,
    };

    let response;
    try {
      if (visitId) {
        response = await apiClient.put(`/api/v1/visits/${visitId}`, payload);
      } else {
        response = await apiClient.post(
          `/api/v1/places/${placeId}/visits`,
          payload
        );
      }
      const result = await response.json();
      if (response.ok) {
        setStatusMessage(
          this.elements.statusMessage,
          `Visit ${visitId ? "updated" : "scheduled"} successfully!`,
          "success"
        );
        if (this.onVisitSavedCallback) this.onVisitSavedCallback(result);
        setTimeout(() => {
          if (this.hideCallback) this.hideCallback();
        }, 1500);
      } else {
        setStatusMessage(
          this.elements.statusMessage,
          result.detail ||
            `Failed to ${visitId ? "update" : "schedule"} visit.`,
          "error"
        );
        if (this.elements.submitBtn) this.elements.submitBtn.disabled = false;
      }
    } catch (error) {
      console.error(
        `Error ${visitId ? "updating" : "scheduling"} visit:`,
        error
      );
      setStatusMessage(
        this.elements.statusMessage,
        `An error occurred. Please try again.`,
        "error"
      );
      if (this.elements.submitBtn) this.elements.submitBtn.disabled = false;
    }
  },
};
export default visitForm;
