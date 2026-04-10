const tabShell = document.querySelector("[data-default-tab]");

const escapeHtml = (value) =>
  String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");

const createSessionId = () => {
  if (window.crypto && typeof window.crypto.randomUUID === "function") {
    return window.crypto.randomUUID();
  }
  return `job-alert-${Date.now()}-${Math.random().toString(16).slice(2)}`;
};

const postUiSession = async (url, sessionId) => {
  const payload = new URLSearchParams({ session_id: sessionId });
  const response = await fetch(url, {
    method: "POST",
    body: payload,
    headers: { Accept: "application/json" },
    keepalive: true,
  });
  return response;
};

let uiSessionId = "";

try {
  uiSessionId = window.sessionStorage.getItem("jobAlertUiSessionId") || "";
  if (!uiSessionId) {
    uiSessionId = createSessionId();
    window.sessionStorage.setItem("jobAlertUiSessionId", uiSessionId);
  }
} catch (error) {
  uiSessionId = createSessionId();
}

if (uiSessionId) {
  const startHeartbeat = async () => {
    try {
      await postUiSession("/ui/session/start", uiSessionId);
    } catch (error) {
      console.error("UI session start failed", error);
    }
  };

  const pingHeartbeat = async () => {
    try {
      await postUiSession("/ui/session/ping", uiSessionId);
    } catch (error) {
      console.error("UI session ping failed", error);
    }
  };

  const stopHeartbeat = () => {
    const payload = new URLSearchParams({ session_id: uiSessionId });
    if (navigator.sendBeacon) {
      navigator.sendBeacon("/ui/session/stop", payload);
      return;
    }
    void fetch("/ui/session/stop", {
      method: "POST",
      body: payload,
      headers: { Accept: "application/json" },
      keepalive: true,
    });
  };

  void startHeartbeat();
  window.setInterval(() => {
    void pingHeartbeat();
  }, 20000);
  window.addEventListener("beforeunload", stopHeartbeat);
  window.addEventListener("pagehide", stopHeartbeat);
}

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

const runProgressModal = document.getElementById("run-progress-modal");

if (runProgressModal) {
  const runForms = document.querySelectorAll("[data-run-progress]");
  const closeButtons = runProgressModal.querySelectorAll("[data-close-run-progress]");
  const titleNode = document.getElementById("run-progress-title");
  const subtitleNode = document.getElementById("run-progress-subtitle");
  const percentNode = document.getElementById("run-progress-percent");
  const countNode = document.getElementById("run-progress-count");
  const fillNode = document.getElementById("run-progress-fill");
  const metaNode = document.getElementById("run-progress-meta");
  const currentStepNode = document.getElementById("run-progress-current-step");
  const currentSiteNode = document.getElementById("run-progress-current-site");
  const eventsNode = document.getElementById("run-progress-events");
  const summaryPanel = document.getElementById("run-progress-summary-panel");
  const summaryNode = document.getElementById("run-progress-summary");
  const openLink = document.getElementById("run-progress-open-link");

  let activeTaskId = null;
  let pollTimer = null;
  let autoRefreshTimer = null;

  const openProgress = () => {
    runProgressModal.classList.remove("hidden");
  };

  const closeProgress = () => {
    runProgressModal.classList.add("hidden");
  };

  const clearProgressTimers = () => {
    if (pollTimer) {
      window.clearInterval(pollTimer);
      pollTimer = null;
    }
    if (autoRefreshTimer) {
      window.clearTimeout(autoRefreshTimer);
      autoRefreshTimer = null;
    }
  };

  const renderRunEvents = (events) => {
    if (!events || !events.length) {
      eventsNode.innerHTML = "<p class=\"small\">Waiting for the first progress update...</p>";
      return;
    }
    eventsNode.innerHTML = events
      .slice()
      .reverse()
      .map(
        (message) => `
          <article class="diag-item">
            <div class="small">${escapeHtml(message)}</div>
          </article>
        `,
      )
      .join("");
  };

  const renderRunTask = (task) => {
    const status = task.status || "running";
    const percent = Number(task.percent || 0);
    const totalSites = Number(task.total_sites || 0);
    const completedSites = Number(task.completed_sites || 0);
    const redirectUrl = task.redirect_url || "/?tab=diagnostics";

    titleNode.textContent = status === "completed" ? "Scrape Run Complete" : status === "failed" ? "Scrape Run Failed" : "Scrape Run In Progress";
    subtitleNode.textContent = task.message || "Running...";
    percentNode.textContent = `${percent}%`;
    countNode.textContent = `${completedSites} of ${totalSites} site${totalSites === 1 ? "" : "s"} completed`;
    fillNode.style.width = `${Math.max(0, Math.min(100, percent))}%`;

    currentStepNode.textContent = task.message || "Running...";
    currentSiteNode.textContent = task.current_site ? `Current site: ${task.current_site}` : "Current site: none right now";
    metaNode.innerHTML = `
      <div class="preview-meta-row">
        <span class="preview-status ${status === "completed" ? "success" : status === "failed" ? "failure" : "success"}">status: ${escapeHtml(status)}</span>
        <span class="small">Started: ${escapeHtml(task.started_at || "-")}</span>
        ${task.finished_at ? `<span class="small">Finished: ${escapeHtml(task.finished_at)}</span>` : ""}
      </div>
    `;

    renderRunEvents(task.events || []);

    if (task.summary_text) {
      summaryPanel.classList.remove("hidden");
      summaryNode.textContent = task.summary_text;
    } else {
      summaryPanel.classList.add("hidden");
      summaryNode.textContent = "";
    }

    if (status === "completed" || status === "failed") {
      openLink.classList.remove("hidden");
      openLink.href = redirectUrl;
      if (status === "completed" && !autoRefreshTimer) {
        autoRefreshTimer = window.setTimeout(() => {
          window.location.href = redirectUrl;
        }, 1600);
      }
    } else {
      openLink.classList.add("hidden");
      openLink.href = redirectUrl;
    }
  };

  const pollRunTask = async () => {
    if (!activeTaskId) {
      return;
    }
    try {
      const response = await fetch(`/run-now/status/${encodeURIComponent(activeTaskId)}`, {
        headers: { Accept: "application/json" },
      });
      const payload = await response.json();
      if (!response.ok || !payload.ok) {
        throw new Error(payload.error || "Could not read run progress.");
      }
      renderRunTask(payload.task);
      if (payload.task.status === "completed" || payload.task.status === "failed") {
        if (pollTimer) {
          window.clearInterval(pollTimer);
          pollTimer = null;
        }
      }
    } catch (error) {
      subtitleNode.textContent = "Could not update run progress";
      currentStepNode.textContent = error.message || "Unknown error.";
      if (pollTimer) {
        window.clearInterval(pollTimer);
        pollTimer = null;
      }
    }
  };

  const startRunProgress = async (form) => {
    const submitButton = form.querySelector('button[type="submit"]');
    const originalLabel = submitButton ? submitButton.textContent : "";
    const formData = new FormData(form);

    if (wizard && !wizard.classList.contains("hidden")) {
      wizard.classList.add("hidden");
    }

    clearProgressTimers();
    activeTaskId = null;
    titleNode.textContent = "Scrape Run In Progress";
    subtitleNode.textContent = "Starting the scrape run...";
    percentNode.textContent = "0%";
    countNode.textContent = "0 of 0 sites completed";
    fillNode.style.width = "0%";
    metaNode.innerHTML = "";
    currentStepNode.textContent = "Starting the scrape run...";
    currentSiteNode.textContent = "Current site: not started yet";
    eventsNode.innerHTML = "<p class=\"small\">Starting the scraper...</p>";
    summaryPanel.classList.add("hidden");
    summaryNode.textContent = "";
    openLink.classList.add("hidden");
    openProgress();

    if (submitButton) {
      submitButton.disabled = true;
      submitButton.textContent = "Starting...";
    }

    try {
      const response = await fetch("/run-now/start", {
        method: "POST",
        body: formData,
        headers: { Accept: "application/json" },
      });
      const payload = await response.json();
      if (!response.ok || !payload.ok) {
        throw new Error(payload.error || "Could not start the scrape run.");
      }
      activeTaskId = payload.task_id;
      renderRunTask(payload.task);
      await pollRunTask();
      if (!pollTimer) {
        pollTimer = window.setInterval(() => {
          void pollRunTask();
        }, 1000);
      }
    } catch (error) {
      titleNode.textContent = "Scrape Run Failed To Start";
      subtitleNode.textContent = error.message || "Unknown error.";
      currentStepNode.textContent = "The run did not start.";
      currentSiteNode.textContent = "";
      renderRunEvents([error.message || "Unknown error."]);
      openLink.classList.remove("hidden");
    } finally {
      if (submitButton) {
        submitButton.disabled = false;
        submitButton.textContent = originalLabel;
      }
    }
  };

  runForms.forEach((form) => {
    form.addEventListener("submit", (event) => {
      event.preventDefault();
      void startRunProgress(form);
    });
  });

  closeButtons.forEach((button) => {
    button.addEventListener("click", closeProgress);
  });

  runProgressModal.addEventListener("click", (event) => {
    if (event.target === runProgressModal) {
      closeProgress();
    }
  });
}
