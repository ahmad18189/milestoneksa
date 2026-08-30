# Copyright (c) 2026, Milestoneksa and contributors
# For license information, please see license.txt

from erpnext.projects.doctype.task.task import Task as ERPNextTask


class Task(ERPNextTask):
	"""Allow child Expected End Date beyond the parent task date.

	Users may change planned dates freely; parent bounds are expanded separately
	by project task updates when needed.
	"""

	def validate_parent_expected_end_date(self):
		return
