/**
 * visitForm.js
 * Manages interactions and state for the Plan/Edit Visit form.
 * Updated for SPA-Lite behavior to update the map without reloading.
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
        if (this.currentVisitData && this.currentPlaceData) {
          if (window.showIcsCustomizeModal) {
            window.showIcsCustomizeModal(
              this.currentVisitData,
              this.currentPlaceData,
            );
          }
        }
      });
    }
  },

  populateForm(placeData, visitDataToEdit = null) {
    if (!this.elements.form || !placeData || !placeData.id) return false;

    this.currentPlaceData = placeData;
    this.currentVisitData = visitDataToEdit;

    this.elements.form.reset();
    setStatusMessage(this.elements.statusMessage, "", "info");
    if (this.elements.calendarActionDiv)
      this.elements.calendarActionDiv.style.display = "none";

    if (this.elements.placeTitleSpan)
      this.elements.placeTitleSpan.textContent = `"${
        placeData.name || "Unknown Place"
      }"`;
    if (this.elements.placeIdInput)
      this.elements.placeIdInput.value = placeData.id;

    if (visitDataToEdit) {
      if (this.elements.formTitle)
        this.elements.formTitle.textContent = "Edit Visit for:";
      if (this.elements.visitIdInput)
        this.elements.visitIdInput.value = visitDataToEdit.id;
      if (this.elements.submitBtn)
        this.elements.submitBtn.textContent = "Save Changes";

      if (this.elements.dateInput && visitDataToEdit.visit_datetime) {
        this.elements.dateInput.value = new Date(visitDataToEdit.visit_datetime)
          .toISOString()
          .split("T")[0];
      }
      if (this.elements.timeInput && visitDataToEdit.visit_datetime) {
        const timeStr = new Date(visitDataToEdit.visit_datetime)
          .toTimeString()
          .split(" ")[0];
        this.elements.timeInput.value = timeStr.substring(0, 5);
      }

      const savedVisitDate = new Date(visitDataToEdit.visit_datetime);
      if (savedVisitDate >= new Date() && this.elements.calendarActionDiv) {
        this.elements.calendarActionDiv.style.display = "block";
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
    if (!this.elements.form || !this.currentPlaceData?.id) return;

    setStatusMessage(this.elements.statusMessage, "Saving visit...", "loading");
    if (this.elements.submitBtn) this.elements.submitBtn.disabled = true;

    const placeId = this.currentPlaceData.id;
    const visitIdBeingEdited = this.currentVisitData?.id || null;
    const dateValue = this.elements.dateInput.value;
    const timeValue = this.elements.timeInput.value;

    if (!dateValue || !timeValue) {
      setStatusMessage(
        this.elements.statusMessage,
        "Date and Time are required.",
        "error",
      );
      if (this.elements.submitBtn) this.elements.submitBtn.disabled = false;
      return;
    }

    const localDateTime = new Date(`${dateValue}T${timeValue}:00`);
    const visit_datetime_iso = localDateTime.toISOString();

    try {
      let response;
      if (visitIdBeingEdited) {
        const formData = new FormData();
        formData.append("visit_datetime", visit_datetime_iso);
        response = await apiClient.fetch(
          `/api/v1/visits/${visitIdBeingEdited}`,
          {
            method: "PUT",
            body: formData,
          },
        );
      } else {
        const payload = {
          place_id: parseInt(placeId),
          visit_datetime: visit_datetime_iso,
        };
        response = await apiClient.post(
          `/api/v1/places/${placeId}/visits`,
          payload,
        );
      }

      const result = await response.json();

      if (response.ok) {
        this.currentVisitData = result;
        setStatusMessage(
          this.elements.statusMessage,
          `Visit ${visitIdBeingEdited ? "updated" : "scheduled"} successfully!`,
          "success",
        );

        const savedVisitDate = new Date(this.currentVisitData.visit_datetime);
        if (savedVisitDate >= new Date() && this.elements.calendarActionDiv) {
          this.elements.calendarActionDiv.style.display = "block";
        }

        if (this.onVisitSavedCallback) {
          this.onVisitSavedCallback(result);
        }

        if (!visitIdBeingEdited && this.elements.formTitle) {
          this.elements.formTitle.textContent = "Edit Visit for:";
        }
        if (this.elements.visitIdInput && this.currentVisitData.id) {
          this.elements.visitIdInput.value = this.currentVisitData.id;
        }
        if (this.elements.submitBtn) {
          this.elements.submitBtn.textContent = "Save Changes";
        }
      } else {
        setStatusMessage(
          this.elements.statusMessage,
          result.detail || "Failed to save visit.",
          "error",
        );
      }
    } catch (error) {
      console.error("Error saving visit:", error);
      setStatusMessage(
        this.elements.statusMessage,
        "An error occurred. Please try again.",
        "error",
      );
    } finally {
      if (this.elements.submitBtn) this.elements.submitBtn.disabled = false;
    }
  },
};

export default visitForm;
