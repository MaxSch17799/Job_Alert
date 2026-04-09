const menu = document.getElementById("keyword-menu");
const termInput = document.getElementById("keyword-menu-term");
const bucketInput = document.getElementById("keyword-menu-bucket");

if (menu && termInput && bucketInput) {
  document.addEventListener("contextmenu", (event) => {
    const chip = event.target.closest(".chip.site-only");
    if (!chip) {
      menu.classList.add("hidden");
      return;
    }
    event.preventDefault();
    termInput.value = chip.dataset.term || "";
    bucketInput.value = chip.dataset.bucket || "";
    menu.style.left = `${event.clientX}px`;
    menu.style.top = `${event.clientY}px`;
    menu.classList.remove("hidden");
  });

  document.addEventListener("click", (event) => {
    if (!event.target.closest("#keyword-menu")) {
      menu.classList.add("hidden");
    }
  });
}
