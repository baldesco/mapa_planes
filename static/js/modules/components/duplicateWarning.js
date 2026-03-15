/**
 * duplicateWarning.js
 * Handles the logic for showing a custom warning modal when potential duplicate places are detected.
 */

const duplicateWarning = {
  elements: {
    modal: null,
    list: null,
    proceedBtn: null,
    cancelBtn: null,
  },
  onConfirm: null,
  onCancel: null,

  init() {
    this.cacheDOMElements();
    this.setupEventListeners();
  },

  cacheDOMElements() {
    this.elements.modal = document.getElementById("duplicate-warning-modal");
    this.elements.list = document.getElementById("duplicate-places-list");
    this.elements.proceedBtn = document.getElementById("duplicate-proceed-btn");
    this.elements.cancelBtn = document.getElementById("duplicate-cancel-btn");
  },

  setupEventListeners() {
    if (this.elements.proceedBtn) {
      this.elements.proceedBtn.addEventListener("click", () => {
        this.hide();
        if (this.onConfirm) this.onConfirm();
      });
    }

    if (this.elements.cancelBtn) {
      this.elements.cancelBtn.addEventListener("click", () => {
        this.hide();
        if (this.onCancel) this.onCancel();
      });
    }
  },

  /**
   * Shows the duplicate warning modal with details about the potential duplicates.
   * @param {Array} duplicates - List of place objects.
   * @param {Function} onConfirm - Callback if user decides to proceed.
   * @param {Function} onCancel - Callback if user decides to cancel.
   */
  show(duplicates, onConfirm, onCancel) {
    if (!this.elements.modal || !this.elements.list) return;

    this.onConfirm = onConfirm;
    this.onCancel = onCancel;

    this.renderDuplicates(duplicates);
    this.elements.modal.style.display = "block";
    this.elements.modal.scrollIntoView({ behavior: "smooth", block: "center" });
  },

  hide() {
    if (this.elements.modal) {
      this.elements.modal.style.display = "none";
    }
  },

  renderDuplicates(duplicates) {
    this.elements.list.innerHTML = "";

    duplicates.forEach((place) => {
      const card = document.createElement("div");
      card.className = "duplicate-place-card";

      const createdDate = new Date(place.created_at).toLocaleDateString(undefined, {
        year: "numeric",
        month: "long",
        day: "numeric",
      });

      const visitCount = place.visits ? place.visits.length : 0;

      card.innerHTML = `
        <h4>${place.name}</h4>
        <p><strong>Category:</strong> ${place.category.charAt(0).toUpperCase() + place.category.slice(1)}</p>
        <div class="meta-row">
            <span class="meta-item"><i class="fas fa-calendar-alt"></i> Added: ${createdDate}</span>
            <span class="meta-item"><i class="fas fa-walking"></i> Visits: ${visitCount}</span>
        </div>
        ${place.description ? `<p class="description">"${place.description}"</p>` : ""}
      `;

      this.elements.list.appendChild(card);
    });
  },
};

export default duplicateWarning;
