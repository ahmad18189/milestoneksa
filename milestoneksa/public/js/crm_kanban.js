(function () {
	const KNOWN_COLUMNS = new Set([
		"backlog",
		"todo",
		"in-progress",
		"done",
		"canceled",
		"cancelled",
		"new",
		"contacted",
		"nurture",
		"qualified",
		"converted",
		"unqualified",
		"junk",
	]);

	function slugify(value) {
		return String(value || "")
			.trim()
			.toLowerCase()
			.replace(/[^\w\s-]/g, "")
			.replace(/\s+/g, "-")
			.replace(/-+/g, "-");
	}

	function isKanbanRoute() {
		return /\/view\/kanban(?:\/|$|\?)/.test(window.location.pathname);
	}

	function enhanceKanban() {
		if (!isKanbanRoute()) {
			document.body.classList.remove("milestone-crm-kanban-active");
			return;
		}

		document.body.classList.add("milestone-crm-kanban-active");

		const board = document.querySelector(".flex.overflow-x-auto.h-full");
		if (board) {
			board.classList.add("milestone-kanban-board");
		}

		const columns = document.querySelectorAll("[data-column]");
		columns.forEach((columnEl, index) => {
			const columnName = columnEl.dataset.column;
			const slug = slugify(columnName);
			const wrapper = columnEl.closest(".min-w-72");
			if (!wrapper) return;

			wrapper.classList.add("milestone-kanban-col");
			wrapper.classList.forEach((className) => {
				if (
					className.startsWith("milestone-kanban-col--") &&
					className !== "milestone-kanban-col"
				) {
					wrapper.classList.remove(className);
				}
			});

			if (KNOWN_COLUMNS.has(slug)) {
				wrapper.classList.add(`milestone-kanban-col--${slug}`);
			} else {
				wrapper.classList.add(`milestone-kanban-col--col-${index % 6}`);
			}

			columnEl.querySelectorAll("[data-name]").forEach((card) => {
				card.classList.add("milestone-kanban-card");
			});
		});
	}

	function scheduleEnhance() {
		window.requestAnimationFrame(enhanceKanban);
	}

	const observer = new MutationObserver(scheduleEnhance);
	observer.observe(document.body, { childList: true, subtree: true });

	window.addEventListener("popstate", scheduleEnhance);
	window.addEventListener("hashchange", scheduleEnhance);

	const originalPushState = history.pushState;
	history.pushState = function pushState(...args) {
		originalPushState.apply(this, args);
		scheduleEnhance();
	};

	const originalReplaceState = history.replaceState;
	history.replaceState = function replaceState(...args) {
		originalReplaceState.apply(this, args);
		scheduleEnhance();
	};

	scheduleEnhance();
	setTimeout(scheduleEnhance, 500);
	setTimeout(scheduleEnhance, 1500);
})();
