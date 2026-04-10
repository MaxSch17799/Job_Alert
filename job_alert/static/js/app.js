const tabShell = document.querySelector("[data-default-tab]");

const escapeHtml = (value) =>
  String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");

let activateTab = () => {};

if (tabShell) {
  const defaultTab = tabShell.dataset.defaultTab || "setup";
  const tabButtons = Array.from(document.querySelectorAll("[data-tab-button]"));
  const tabPanels = Array.from(document.querySelectorAll("[data-tab-panel]"));

  activateTab = (tabName) => {
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

document.querySelectorAll("[data-close-flash]").forEach((button) => {
  button.addEventListener("click", () => {
    const flash = button.closest("[data-flash]");
    if (flash) {
      flash.remove();
    }
  });
});

const wizard = document.getElementById("setup-wizard");

if (wizard) {
  const topicButtons = Array.from(wizard.querySelectorAll("[data-wizard-topic-button]"));
  const topicPanels = Array.from(wizard.querySelectorAll("[data-wizard-topic-panel]"));
  const navButtons = wizard.querySelectorAll("[data-wizard-topic-nav]");
  const openButtons = document.querySelectorAll("[data-open-wizard]");
  const closeButtons = wizard.querySelectorAll("[data-close-wizard]");
  const orderedTopics = topicButtons.map((button) => button.dataset.wizardTopicButton);
  let currentTopic = wizard.dataset.startTopic || orderedTopics[0] || "email";

  const renderTopic = () => {
    topicButtons.forEach((button) => {
      button.classList.toggle("active", button.dataset.wizardTopicButton === currentTopic);
    });
    topicPanels.forEach((panel) => {
      panel.classList.toggle("hidden", panel.dataset.wizardTopicPanel !== currentTopic);
    });
  };

  const openWizard = () => {
    wizard.classList.remove("hidden");
    renderTopic();
  };

  const closeWizard = () => wizard.classList.add("hidden");

  topicButtons.forEach((button) => {
    button.addEventListener("click", () => {
      currentTopic = button.dataset.wizardTopicButton;
      renderTopic();
    });
  });

  navButtons.forEach((button) => {
    button.addEventListener("click", () => {
      const direction = button.dataset.wizardTopicNav;
      const currentIndex = orderedTopics.indexOf(currentTopic);
      if (currentIndex === -1) {
        currentTopic = orderedTopics[0];
        renderTopic();
        return;
      }
      if (direction === "prev" && currentIndex > 0) {
        currentTopic = orderedTopics[currentIndex - 1];
      } else if (direction === "next" && currentIndex < orderedTopics.length - 1) {
        currentTopic = orderedTopics[currentIndex + 1];
      } else if (direction === "next") {
        closeWizard();
        return;
      }
      renderTopic();
    });
  });

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

  renderTopic();

  if (wizard.dataset.openOnLoad === "true") {
    openWizard();
  }
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

const previewModal = document.getElementById("site-preview-modal");

if (previewModal) {
  const titleNode = document.getElementById("site-preview-title");
  const subtitleNode = document.getElementById("site-preview-subtitle");
  const metaNode = document.getElementById("site-preview-meta");
  const bodyNode = document.getElementById("site-preview-body");
  const closeButtons = previewModal.querySelectorAll("[data-close-preview]");
  const previewButtons = document.querySelectorAll("[data-site-preview]");

  const closePreview = () => {
    previewModal.classList.add("hidden");
  };

  const openPreview = () => {
    previewModal.classList.remove("hidden");
  };

  const renderLinks = (sourceUrl, resolvedUrl) => {
    const items = [];
    if (sourceUrl) {
      items.push(
        `<a class="site-link" href="${escapeHtml(sourceUrl)}" target="_blank" rel="noreferrer">Open website</a>`,
      );
    }
    if (resolvedUrl && resolvedUrl !== sourceUrl) {
      items.push(
        `<a class="site-link" href="${escapeHtml(resolvedUrl)}" target="_blank" rel="noreferrer">Open resolved endpoint</a>`,
      );
    }
    return items.join(" ");
  };

  const renderJobs = (payload) => {
    if (!payload.jobs.length) {
      return `
        <article class="preview-job">
          <h3>No matching jobs found right now</h3>
          <p class="small">The site check worked, but nothing on the board currently matches your filters for this site.</p>
          <p class="small">${renderLinks(payload.source_url, payload.resolved_url)}</p>
        </article>
      `;
    }

    return `
      <div class="preview-job-list">
        ${payload.jobs
          .map((job) => {
            const metaBits = [];
            if (job.location) {
              metaBits.push(`<span>${escapeHtml(job.location)}</span>`);
            }
            if (job.posted_text) {
              metaBits.push(`<span>${escapeHtml(job.posted_text)}</span>`);
            }
            return `
              <article class="preview-job">
                <div class="preview-job-header">
                  <h3><a class="site-link" href="${escapeHtml(job.url)}" target="_blank" rel="noreferrer">${escapeHtml(job.title)}</a></h3>
                </div>
                ${metaBits.length ? `<div class="preview-job-meta">${metaBits.join("<span class=\"dot\">|</span>")}</div>` : ""}
                ${
                  Array.isArray(job.matched_terms) && job.matched_terms.length
                    ? `<div class="small">Matched terms: ${escapeHtml(job.matched_terms.join(", "))}</div>`
                    : ""
                }
              </article>
            `;
          })
          .join("")}
      </div>
    `;
  };

  const renderPayload = (payload) => {
    titleNode.textContent = `${payload.label} | Current Matching Jobs`;

    if (!payload.ok) {
      subtitleNode.textContent = "Live check failed";
      metaNode.innerHTML = `
        <div class="preview-status failure">The site did not return usable results.</div>
        <div class="small">${payload.warning ? escapeHtml(payload.warning) : "Unknown error."}</div>
        <div class="small">${renderLinks(payload.source_url, payload.resolved_url)}</div>
      `;
      bodyNode.innerHTML = `
        <article class="preview-job">
          <h3>What to do next</h3>
          <p class="small">Check the website manually with the link above. If the site still works in your browser, the board structure may have changed and the scraper adapter needs updating.</p>
          ${
            Array.isArray(payload.notes) && payload.notes.length
              ? `<p class="small">Notes: ${escapeHtml(payload.notes.join(" | "))}</p>`
              : ""
          }
        </article>
      `;
      return;
    }

    subtitleNode.textContent = `${payload.matched_count} matching jobs found out of ${payload.jobs_found} live jobs on this site.`;
    metaNode.innerHTML = `
      <div class="preview-meta-row">
        <span class="preview-status success">adapter: ${escapeHtml(payload.adapter_name || "unknown")}</span>
        <span class="small">${renderLinks(payload.source_url, payload.resolved_url)}</span>
      </div>
      ${
        Array.isArray(payload.notes) && payload.notes.length
          ? `<div class="small">Notes: ${escapeHtml(payload.notes.join(" | "))}</div>`
          : ""
      }
    `;
    bodyNode.innerHTML = renderJobs(payload);
  };

  const loadPreview = async (button) => {
    const siteId = button.dataset.siteId;
    const originalLabel = button.textContent;

    button.disabled = true;
    button.textContent = "Loading...";
    titleNode.textContent = "Site Results";
    subtitleNode.textContent = "Loading current jobs...";
    metaNode.innerHTML = "";
    bodyNode.innerHTML = "<p class=\"small\">Running a live site check. This can take a few seconds.</p>";
    openPreview();

    try {
      const response = await fetch(`/sites/${encodeURIComponent(siteId)}/preview`, {
        headers: { Accept: "application/json" },
      });
      const payload = await response.json();
      if (!response.ok) {
        throw new Error(payload.error || "Preview request failed.");
      }
      renderPayload(payload);
    } catch (error) {
      titleNode.textContent = "Site Results";
      subtitleNode.textContent = "Preview failed";
      metaNode.innerHTML = "";
      bodyNode.innerHTML = `
        <article class="preview-job">
          <h3>Could not load site preview</h3>
          <p class="small">${escapeHtml(error.message || "Unknown error.")}</p>
        </article>
      `;
    } finally {
      button.disabled = false;
      button.textContent = originalLabel;
    }
  };

  previewButtons.forEach((button) => {
    button.addEventListener("click", () => {
      void loadPreview(button);
    });
  });

  closeButtons.forEach((button) => {
    button.addEventListener("click", closePreview);
  });

  previewModal.addEventListener("click", (event) => {
    if (event.target === previewModal) {
      closePreview();
    }
  });

  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape") {
      if (!previewModal.classList.contains("hidden")) {
        closePreview();
      } else if (wizard && !wizard.classList.contains("hidden")) {
        wizard.classList.add("hidden");
      }
    }
  });
}
