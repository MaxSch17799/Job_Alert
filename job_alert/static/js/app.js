const tabShell = document.querySelector("[data-default-tab]");

if (tabShell) {
  const defaultTab = tabShell.dataset.defaultTab || "setup";
  const tabButtons = Array.from(document.querySelectorAll("[data-tab-button]"));
  const tabPanels = Array.from(document.querySelectorAll("[data-tab-panel]"));

  const activateTab = (tabName) => {
    tabButtons.forEach((button) => {
      button.classList.toggle("active", button.dataset.tabButton === tabName);
    });
    tabPanels.forEach((panel) => {
      panel.classList.toggle("hidden", panel.dataset.tabPanel !== tabName);
    });
  };

  activateTab(defaultTab);

  tabButtons.forEach((button) => {
    button.addEventListener("click", () => activateTab(button.dataset.tabButton));
  });

  document.querySelectorAll("[data-tab-target]").forEach((button) => {
    button.addEventListener("click", () => {
      const tabTarget = button.dataset.tabTarget;
      if (tabTarget) {
        activateTab(tabTarget);
      }
      const scrollTarget = button.dataset.scrollTarget;
      if (scrollTarget) {
        const target = document.getElementById(scrollTarget);
        if (target) {
          target.scrollIntoView({ behavior: "smooth", block: "start" });
        }
      }
    });
  });
}

const wizard = document.getElementById("setup-wizard");

if (wizard) {
  const steps = Array.from(wizard.querySelectorAll("[data-wizard-step]"));
  const backButton = wizard.querySelector("[data-wizard-back]");
  const nextButton = wizard.querySelector("[data-wizard-next]");
  const openButtons = document.querySelectorAll("[data-open-wizard]");
  const closeButtons = wizard.querySelectorAll("[data-close-wizard]");
  let currentStep = 0;

  const renderStep = () => {
    steps.forEach((step, index) => {
      step.classList.toggle("hidden", index !== currentStep);
    });
    if (backButton) {
      backButton.disabled = currentStep === 0;
    }
    if (nextButton) {
      nextButton.textContent = currentStep === steps.length - 1 ? "Finish" : "Next";
    }
  };

  const openWizard = () => {
    wizard.classList.remove("hidden");
    currentStep = 0;
    renderStep();
  };

  const closeWizard = () => wizard.classList.add("hidden");

  openButtons.forEach((button) => {
    button.addEventListener("click", openWizard);
  });

  closeButtons.forEach((button) => {
    button.addEventListener("click", closeWizard);
  });

  wizard.addEventListener("click", (event) => {
    if (event.target === wizard) {
      closeWizard();
    }
  });

  if (backButton) {
    backButton.addEventListener("click", () => {
      if (currentStep > 0) {
        currentStep -= 1;
        renderStep();
      }
    });
  }

  if (nextButton) {
    nextButton.addEventListener("click", () => {
      if (currentStep < steps.length - 1) {
        currentStep += 1;
        renderStep();
      } else {
        closeWizard();
      }
    });
  }

  renderStep();
}

document.querySelectorAll("[data-copy-target]").forEach((button) => {
  button.addEventListener("click", async () => {
    const target = document.getElementById(button.dataset.copyTarget || "");
    if (!target) {
      return;
    }
    const text = target.textContent || target.value || "";
    try {
      await navigator.clipboard.writeText(text);
      const original = button.textContent;
      button.textContent = "Copied";
      window.setTimeout(() => {
        button.textContent = original;
      }, 1200);
    } catch (error) {
      console.error("Copy failed", error);
    }
  });
});
