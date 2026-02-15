# Copyright (c) 2025, ahmed and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import getdate


class ProjectAttachment(Document):
	def validate(self):
		# Set upload_date to creation date
		# For existing documents, creation will be set
		# For new documents, it will be set during save, but we set it here too
		if self.creation:
			self.upload_date = getdate(self.creation)
		elif self.is_new():
			# For new documents, creation will be set during save
			# Set upload_date to today, it will be updated to match creation on next save
			from frappe.utils import today
			self.upload_date = today()
