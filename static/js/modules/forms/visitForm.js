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
    visitIdInput: null, // For editing
    dateInput: null,
    timeInput: null,
    reminderEnabledCheckbox: null,
    reminderOptionsDiv: null,
    reminderOffsetCheckboxes: [], // Array of checkbox elements
    statusMessage: null,
    submitBtn: null,
    cancelBtn: null,
  },
  currentPlaceData: null, // To store parent place data when planning/editing a visit
  currentVisitData: null, // To store existing visit data when editing
  hideCallback: null,
  onVisitSavedCallback: null, // Callback to refresh main UI after saving

  init(hideFn, onSaveFn) {
    console.debug("Visit Form: Initializing...");
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
    this.elements.formTitle = this.elements.wrapper.querySelector("h2"); // More robust
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
    if (!this.elements.form) return false;
    this.currentPlaceData = placeData;
    this.currentVisitData = visitData; // Store existing visit data if editing

    this.elements.form.reset(); // Clear previous state
    if (this.elements.reminderOptionsDiv)
      this.elements.reminderOptionsDiv.style.display = "none";
    setStatusMessage(this.elements.statusMessage, "", "info");

    if (this.elements.placeTitleSpan) {
      this.elements.placeTitleSpan.textContent = `"${
        placeData.name || "Unknown Place"
      }"`;
    }
    if (this.elements.placeIdInput) {
      this.elements.placeIdInput.value = placeData.id;
    }

    if (visitData) {
      // Editing existing visit
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
          .split(" ")[0]; // HH:MM:SS
        this.elements.timeInput.value = timeStr.substring(0, 5); // HH:MM
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
      // Planning new visit
      if (this.elements.formTitle)
        this.elements.formTitle.textContent = "Plan New Visit for:";
      if (this.elements.visitIdInput) this.elements.visitIdInput.value = ""; // Clear visit ID
      if (this.elements.submitBtn)
        this.elements.submitBtn.textContent = "Schedule Visit";
      // Set date to today and time to current time + 1 hour as a sensible default
      const now = new Date();
      now.setHours(now.getHours() + 1);
      now.setMinutes(0); // Round to hour
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
    if (!this.elements.form || !this.currentPlaceData) return;

    setStatusMessage(this.elements.statusMessage, "Saving visit...", "loading");
    if (this.elements.submitBtn) this.elements.submitBtn.disabled = true;

    const formData = new FormData(this.elements.form);
    const placeId = this.currentPlaceData.id;
    const visitId = this.currentVisitData ? this.currentVisitData.id : null;

    const dateValue = formData.get("visit_date");
    const timeValue = formData.get("visit_time");

    if (!dateValue || !timeValue) {
      setStatusMessage(
        this.elements.statusMessage,
        "Date and Time are required.",
        "error"
      );
      if (this.elements.submitBtn) this.elements.submitBtn.disabled = false;
      return;
    }
    // Combine date and time. IMPORTANT: This creates a datetime in the browser's local timezone.
    // The backend needs to be aware of this or expect UTC.
    // For simplicity, we'll send it as is, and Supabase TIMESTAMPTZ will store it as UTC
    // if the input string is ISO 8601 compliant without explicit offset, assuming local time.
    // Or, better, construct ISO string with local offset, then Supabase converts to UTC.
    // For now, let's send local date and time parts. Backend will combine.
    // OR, construct full ISO string here.
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

    const reminderEnabled = this.elements.reminderEnabledCheckbox
      ? this.elements.reminderEnabledCheckbox.checked
      : false;
    let reminderOffsets = [];
    if (reminderEnabled && this.elements.reminderOffsetCheckboxes.length > 0) {
      this.elements.reminderOffsetCheckboxes.forEach((cb) => {
        if (cb.checked) {
          reminderOffsets.push(parseInt(cb.value));
        }
      });
    }

    const payload = {
      place_id: parseInt(placeId),
      visit_datetime: visit_datetime_iso, // Send as ISO string (UTC or with offset)
      reminder_enabled: reminderEnabled,
      reminder_offsets_hours:
        reminderOffsets.length > 0 ? reminderOffsets : null,
      // Review fields are not part of this form
    };

    let response;
    try {
      if (visitId) {
        // Editing existing visit
        const apiUrl = `/api/v1/visits/${visitId}`;
        // For PUT with FormData (if image was part of this form, which it's not now)
        // For now, assuming VisitUpdate for schedule/reminders is JSON
        response = await apiClient.put(apiUrl, payload);
      } else {
        // Creating new visit
        const apiUrl = `/api/v1/places/${placeId}/visits`;
        response = await apiClient.post(apiUrl, payload);
      }

      const result = await response.json();

      if (response.ok) {
        setStatusMessage(
          this.elements.statusMessage,
          `Visit ${visitId ? "updated" : "scheduled"} successfully!`,
          "success"
        );
        if (this.onVisitSavedCallback) {
          this.onVisitSavedCallback(result); // Pass created/updated visit data
        }
        setTimeout(() => {
          // Give time to read success message
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
