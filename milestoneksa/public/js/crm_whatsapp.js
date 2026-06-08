(function () {
	const ROOT_CLASS = "milestone-whatsapp-enhanced";

	function isCrmPage() {
		return window.location.pathname === "/crm" || window.location.pathname.startsWith("/crm/");
	}

	function findBubble(activity) {
		return Array.from(activity.children).find((child) => child.id);
	}

	function enhanceMessages() {
		if (!isCrmPage()) return;

		const activities = Array.from(document.querySelectorAll(".activity.group.flex.gap-2"));
		const messageActivities = activities.filter(findBubble);
		if (!messageActivities.length) return;

		const scrollArea = messageActivities[0].closest(".flex.flex-col.h-full.overflow-y-auto");
		scrollArea?.classList.add("milestone-whatsapp-scroll", ROOT_CLASS);

		const messageList = messageActivities[0].parentElement;
		messageList?.classList.add("milestone-whatsapp-list");

		messageActivities.forEach((activity) => {
			const bubble = findBubble(activity);
			if (!bubble) return;

			const isOutgoing = activity.classList.contains("flex-row-reverse");
			bubble.classList.add("milestone-wa-bubble");
			bubble.classList.toggle("milestone-wa-outgoing", isOutgoing);
			bubble.classList.toggle("milestone-wa-incoming", !isOutgoing);

			const time = bubble.querySelector(".text-2xs");
			time?.classList.add("milestone-wa-time");
		});
	}

	function enhanceComposer() {
		if (!isCrmPage()) return;

		document.querySelectorAll("textarea").forEach((textarea) => {
			const composer = textarea.closest(".flex.items-end.gap-2");
			composer?.classList.add("milestone-wa-composer");
		});
	}

	function enhanceWhatsAppTab() {
		enhanceMessages();
		enhanceComposer();
	}

	const observer = new MutationObserver(enhanceWhatsAppTab);

	function start() {
		enhanceWhatsAppTab();
		observer.observe(document.body, { childList: true, subtree: true });
	}

	if (document.readyState === "loading") {
		document.addEventListener("DOMContentLoaded", start, { once: true });
	} else {
		start();
	}

	window.addEventListener("hashchange", enhanceWhatsAppTab);
	window.addEventListener("popstate", enhanceWhatsAppTab);
})();
