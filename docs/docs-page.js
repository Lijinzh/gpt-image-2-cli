(() => {
  const menuButton = document.querySelector("[data-docs-menu]");
  const sidebar = document.querySelector("[data-docs-sidebar]");
  const header = document.querySelector(".docs-header");
  const search = document.querySelector("[data-docs-search]");

  menuButton?.addEventListener("click", () => {
    const open = sidebar?.classList.toggle("is-open") ?? false;
    menuButton.setAttribute("aria-expanded", String(open));
  });

  sidebar?.addEventListener("click", (event) => {
    if (event.target instanceof HTMLAnchorElement) {
      sidebar.classList.remove("is-open");
      menuButton?.setAttribute("aria-expanded", "false");
    }
  });

  document.addEventListener("keydown", (event) => {
    if (event.key === "/" && document.activeElement !== search) {
      event.preventDefault();
      header?.classList.add("is-searching");
      search?.focus();
    }
    if (event.key === "Escape") {
      sidebar?.classList.remove("is-open");
      menuButton?.setAttribute("aria-expanded", "false");
      header?.classList.remove("is-searching");
    }
  });

  search?.addEventListener("input", () => {
    const query = search.value.trim().toLocaleLowerCase();
    document.querySelectorAll(".doc-nav a").forEach((link) => {
      link.hidden = Boolean(query) && !link.textContent.toLocaleLowerCase().includes(query);
    });
  });

  document.querySelectorAll("pre").forEach((block) => {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "copy-code";
    button.textContent = "复制";
    button.setAttribute("aria-label", "复制代码");
    button.addEventListener("click", async () => {
      const code = block.querySelector("code")?.textContent ?? block.textContent ?? "";
      try {
        await navigator.clipboard.writeText(code.trim());
        button.textContent = "已复制";
      } catch {
        button.textContent = "复制失败";
      }
      window.setTimeout(() => { button.textContent = "复制"; }, 1600);
    });
    block.append(button);
  });

  const tocLinks = [...document.querySelectorAll(".docs-toc a")];
  const headings = tocLinks
    .map((link) => document.querySelector(link.getAttribute("href")))
    .filter(Boolean);
  if ("IntersectionObserver" in window && headings.length) {
    const observer = new IntersectionObserver((entries) => {
      const visible = entries.find((entry) => entry.isIntersecting);
      if (!visible) return;
      tocLinks.forEach((link) => {
        link.classList.toggle("is-active", link.getAttribute("href") === `#${visible.target.id}`);
      });
    }, { rootMargin: "-18% 0px -70%", threshold: 0 });
    headings.forEach((heading) => observer.observe(heading));
  }
})();
