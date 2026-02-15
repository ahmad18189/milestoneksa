# -*- coding: utf-8 -*-
import frappe

def boot_session(bootinfo):
	"""
	Attach pending Desk Announcements for the current user to boot info,
	so they are computed on EVERY login / desk boot.
	"""
	try:
		from milestoneksa.milestoneksa.doctype.desk_announcement.desk_announcement import get_pending_announcements
		bootinfo["desk_announcements"] = get_pending_announcements() or []
	except Exception:
		# Never break the Desk if something goes wrong
		bootinfo["desk_announcements"] = []
