/**
 * visitForm.js
 * Manages interactions and state for the Plan/Edit Visit form.
 * Updated for SPA-lite behavior to prevent full page reloads.
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
    statusMessage: null,
    submitBtn: null,
    cancelBtn: null,
    calendarActionDiv: null,
    addToCalendarBtn: null,
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
    if (!this.elements.wrapper) return;

    this.elements.form = document.getElementById("plan-visit-form");
    this.elements.formTitle = this.elements.wrapper.querySelector("h2");
    this.elements.placeTitleSpan = document.getElementById(
      "plan-visit-place-title",
    );
    this.elements.placeIdInput = document.getElementById("plan-visit-place-id");
    this.elements.visitIdInput = document.getElementById("plan-visit-id");
    this.elements.dateInput = document.getElementById("visit-date");
    this.elements.timeInput = document.getElementById("visit-time");
    this.elements.statusMessage = document.getElementById("plan-visit-status");
    this.elements.submitBtn = document.getElementById("plan-visit-submit-btn");
    this.elements.cancelBtn = document.getElementById("plan-visit-cancel-btn");
    this.elements.calendarActionDiv = document.getElementById(
      "plan-visit-calendar-action",
    );
    this.elements.addToCalendarBtn = document.getElementById(
      "plan-visit-add-to-calendar-btn",
    );
  },

  setupEventListeners() {
    if (!this.elements.form) return;
    this.elements.form.addEventListener("submit", (event) =>
      this.handleSubmit(event),
    );

    if (this.elements.cancelBtn && this.hideCallback) {
      this.elements.cancelBtn.addEventListener("click", () => {
        if (this.elements.calendarActionDiv)
          this.elements.calendarActionDiv.style.display = "none";
        this.hideCallback();
      });
    }

    if (this.elements.addToCalendarBtn) {
      this.elements.addToCalendarBtn.addEventListener("click", () => {
        if (
          this.currentVisitData &&
          this.currentPlaceData &&
          window.showIcsCustomizeModal
        ) {
          window.showIcsCustomizeModal(
            this.currentVisitData,
            this.currentPlaceData,
          );
        }
      });
    }
  },

  populateForm(placeData, visitDataToEdit = null) {
    if (!this.elements.form || !placeData) return false;

    this.currentPlaceData = placeData;
    this.currentVisitData = visitDataToEdit;

    this.elements.form.reset();
    setStatusMessage(this.elements.statusMessage, "", "info");
    if (this.elements.calendarActionDiv)
      this.elements.calendarActionDiv.style.display = "none";

    this.elements.placeTitleSpan.textContent =
      placeData.name || "Unknown Place";
    this.elements.placeIdInput.value = placeData.id;

    if (visitDataToEdit) {
      this.elements.formTitle.textContent = "Edit Visit";
      this.elements.visitIdInput.value = visitDataToEdit.id;
      this.elements.submitBtn.textContent = "Save Changes";

      const dt = new Date(visitDataToEdit.visit_datetime);
      this.elements.dateInput.value = dt.toISOString().split("T")[0];
      this.elements.timeInput.value = dt.toTimeString().substring(0, 5);

      if (dt >= new Date()) {
        this.elements.calendarActionDiv.style.display = "block";
      }
    } else {
      this.elements.formTitle.textContent = "Plan New Visit";
      this.elements.visitIdInput.value = "";
      this.elements.submitBtn.textContent = "Schedule Visit";

      const now = new Date();
      now.setHours(now.getHours() + 1, 0, 0, 0);
      this.elements.dateInput.value = now.toISOString().split("T")[0];
      this.elements.timeInput.value = now.toTimeString().substring(0, 5);
    }

    this.elements.submitBtn.disabled = false;
    return true;
  },

  async handleSubmit(event) {
    event.preventDefault();

    setStatusMessage(this.elements.statusMessage, "Saving...", "loading");
    this.elements.submitBtn.disabled = true;

    const dateValue = this.elements.dateInput.value;
    const timeValue = this.elements.timeInput.value;
    const localDateTime = new Date(`${dateValue}T${timeValue}:00`);

    if (isNaN(localDateTime.getTime())) {
      setStatusMessage(
        this.elements.statusMessage,
        "Invalid date/time.",
        "error",
      );
      this.elements.submitBtn.disabled = false;
      return;
    }

    const visitId = this.elements.visitIdInput.value;
    const payload = {
      visit_datetime: localDateTime.toISOString(),
    };

    try {
      let response;
      if (visitId) {
        const formData = new FormData();
        formData.append("visit_datetime", payload.visit_datetime);
        response = await apiClient.fetch(`/api/v1/visits/${visitId}`, {
          method: "PUT",
          body: formData,
        });
      } else {
        payload.place_id = parseInt(this.elements.placeIdInput.value);
        response = await apiClient.post(
          `/api/v1/places/${payload.place_id}/visits`,
          payload,
        );
      }

      const result = await response.json();

      if (response.ok) {
        this.currentVisitData = result;
        setStatusMessage(
          this.elements.statusMessage,
          "Visit saved!",
          "success",
        );

        if (new Date(result.visit_datetime) >= new Date()) {
          this.elements.calendarActionDiv.style.display = "block";
        }

        if (this.onVisitSavedCallback) {
          this.onVisitSavedCallback(result);
        }
      } else {
        setStatusMessage(
          this.elements.statusMessage,
          result.detail || "Error saving visit.",
          "error",
        );
        this.elements.submitBtn.disabled = false;
      }
    } catch (error) {
      setStatusMessage(
        this.elements.statusMessage,
        "Connection error.",
        "error",
      );
      this.elements.submitBtn.disabled = false;
    }
  },
};

export default visitForm;
