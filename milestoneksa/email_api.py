# Copyright (c) 2025, Milestoneksa
# Email sending via API (Microsoft Graph, SendGrid, etc.) to bypass SMTP port blocking

import base64
from email import message_from_string
from email.utils import getaddresses

import frappe
import requests
from frappe import _


def _queue_send_cache_key(email_queue) -> str:
	name = getattr(email_queue, "name", None) or id(email_queue)
	return f"api_email_sent:{name}"


def _header_addresses(msg, *headers) -> list[str]:
	values = []
	for header in headers:
		values.extend(msg.get_all(header, []))
	return [addr.strip().lower() for _, addr in getaddresses(values) if addr and "@" in addr]


def send_email_via_api(email_queue, sender, recipient, message):
	"""
	Override email sending to use API instead of SMTP.
	This function is called via the 'override_email_send' hook.

	Frappe flushes once per Email Queue Recipient (To and CC). We send the full
	message only once per queue so CC recipients are not turned into separate To emails.
	"""
	cache_key = _queue_send_cache_key(email_queue)
	if frappe.cache.get_value(cache_key):
		return

	try:
		# Get the email account
		email_account_name = email_queue.email_account
		if not email_account_name:
			frappe.throw(_("Email Account not found"))

		email_account = frappe.get_doc("Email Account", email_account_name)

		# Check if OAuth is enabled
		if email_account.auth_method == "OAuth":
			# Use Microsoft Graph API for OAuth accounts (Outlook/Microsoft 365)
			_send_via_microsoft_graph(sender, recipient, message, email_account)
		else:
			# Check which service to use for non-OAuth accounts
			service = email_account.get("service", "").lower()

			if service == "sendgrid":
				_send_via_sendgrid(sender, recipient, message, email_account)
			else:
				frappe.throw(_("API-based sending requires OAuth authentication or SendGrid service"))

		frappe.cache.set_value(cache_key, 1, expires_in_sec=3600)

	except Exception:
		frappe.log_error(
			title=f"API Email Send Failed: {recipient}",
			message=frappe.get_traceback(),
		)
		raise


def _send_via_microsoft_graph(sender, recipient, message, email_account):
	"""Send email using Microsoft Graph API (OAuth)"""
	try:
		# Get OAuth token
		if not email_account.connected_app:
			frappe.throw(_("Connected App not configured for this Email Account"))

		connected_app = frappe.get_doc("Connected App", email_account.connected_app)

		if email_account.backend_app_flow:
			token_cache = connected_app.get_backend_app_token()
		else:
			connected_user = email_account.connected_user
			token_cache = connected_app.get_active_token(connected_user)

		if not token_cache:
			frappe.throw(_("OAuth token not found. Please authorize the email account."))

		access_token = token_cache.get_password("access_token")
		if not access_token:
			frappe.throw(_("Access token not found. Please re-authorize the email account."))

		# Parse the email message
		msg = message_from_string(message.decode("utf-8") if isinstance(message, bytes) else message)

		# Extract sender email (remove display name if present)
		from_addr = sender
		if "<" in sender:
			from_addr = sender.split("<")[1].split(">")[0].strip()

		to_list = _header_addresses(msg, "To")
		cc_list = _header_addresses(msg, "Cc", "CC")
		bcc_list = _header_addresses(msg, "Bcc", "BCC")

		# Fallback when headers are missing (single-recipient flush)
		if not to_list and recipient:
			to_list = [recipient.strip().lower()]

		# Never put CC/BCC addresses into To
		cc_set = set(cc_list)
		bcc_set = set(bcc_list)
		to_list = [addr for addr in to_list if addr not in cc_set and addr not in bcc_set]
		if not to_list and recipient:
			# Current flush target is a CC-only recipient; still deliver once with proper roles
			current = recipient.strip().lower()
			if current in cc_set or current in bcc_set:
				to_list = [addr for addr in _header_addresses(msg, "To") if addr]
			if not to_list:
				to_list = [current]

		email_payload = {
			"message": {
				"subject": msg.get("Subject", "No Subject"),
				"body": {"contentType": "HTML", "content": ""},
				"toRecipients": [{"emailAddress": {"address": addr}} for addr in to_list],
			}
		}

		# Get email content
		html_content = None
		plain_content = None
		attachments = []

		if msg.is_multipart():
			for part in msg.walk():
				content_type = part.get_content_type()
				content_disposition = str(part.get("Content-Disposition", ""))

				# Handle attachments
				if "attachment" in content_disposition:
					filename = part.get_filename()
					if filename:
						attachment_data = part.get_payload(decode=True)
						if attachment_data:
							attachments.append(
								{
									"@odata.type": "#microsoft.graph.fileAttachment",
									"name": filename,
									"contentType": content_type,
									"contentBytes": base64.b64encode(attachment_data).decode("utf-8"),
								}
							)
				# Handle content
				elif content_type == "text/html":
					html_content = part.get_payload(decode=True).decode("utf-8", errors="ignore")
				elif content_type == "text/plain" and not plain_content:
					plain_content = part.get_payload(decode=True).decode("utf-8", errors="ignore")
		else:
			content_type = msg.get_content_type()
			payload = msg.get_payload(decode=True)
			if payload:
				decoded = payload.decode("utf-8", errors="ignore")
				if content_type == "text/html":
					html_content = decoded
				else:
					plain_content = decoded

		# Set content
		if html_content:
			email_payload["message"]["body"]["contentType"] = "HTML"
			email_payload["message"]["body"]["content"] = html_content
		elif plain_content:
			email_payload["message"]["body"]["contentType"] = "Text"
			email_payload["message"]["body"]["content"] = plain_content
		else:
			email_payload["message"]["body"]["content"] = "No content"

		if cc_list:
			email_payload["message"]["ccRecipients"] = [
				{"emailAddress": {"address": addr}} for addr in cc_list
			]

		if bcc_list:
			email_payload["message"]["bccRecipients"] = [
				{"emailAddress": {"address": addr}} for addr in bcc_list
			]

		# Add Reply-To if present
		if msg.get("Reply-To"):
			reply_to = _header_addresses(msg, "Reply-To")
			if reply_to:
				email_payload["message"]["replyTo"] = [
					{"emailAddress": {"address": addr}} for addr in reply_to
				]

		# Add attachments if any
		if attachments:
			email_payload["message"]["attachments"] = attachments

		# Send via Microsoft Graph API
		graph_url = f"https://graph.microsoft.com/v1.0/users/{from_addr}/sendMail"

		headers = {
			"Authorization": f"Bearer {access_token}",
			"Content-Type": "application/json",
		}

		response = requests.post(graph_url, json=email_payload, headers=headers)

		if response.status_code == 202:
			# Success (Microsoft Graph returns 202 Accepted for sendMail)
			frappe.logger().info(
				f"Microsoft Graph API email sent to={to_list} cc={cc_list}"
			)
		elif response.status_code == 401:
			# Token expired, try to refresh
			frappe.throw(_("OAuth token expired. Please re-authorize the email account."))
		else:
			error_msg = response.text
			try:
				error_json = response.json()
				error_msg = error_json.get("error", {}).get("message", error_msg)
			except Exception:
				pass

			frappe.throw(
				_(
					"Microsoft Graph API returned status code: {0}. Error: {1}"
				).format(response.status_code, error_msg)
			)

	except requests.exceptions.RequestException as e:
		frappe.throw(_("Failed to connect to Microsoft Graph API: {0}").format(str(e)))


def _send_via_sendgrid(sender, recipient, message, email_account, use_config_key=False):
	"""Send email using SendGrid API"""
	try:
		from sendgrid import SendGridAPIClient
		from sendgrid.helpers.mail import Mail, Email, To, Content
	except ImportError:
		frappe.throw(_(
			"SendGrid Python library not installed. "
			"Please run: bench pip install sendgrid"
		))
	
	# Parse the email message
	msg = message_from_string(message.decode('utf-8') if isinstance(message, bytes) else message)
	
	# Get API key
	if use_config_key:
		api_key = frappe.conf.get("sendgrid_api_key")
	else:
		# Get API key from Email Account password field
		api_key = email_account.get_password()
	
	if not api_key:
		frappe.throw(_("SendGrid API Key not found"))
	
	# Extract email parts
	subject = msg.get('Subject', 'No Subject')
	from_email = Email(sender)
	to_email = To(recipient)
	
	# Get email content (prefer HTML, fallback to plain text)
	html_content = None
	plain_content = None
	
	if msg.is_multipart():
		for part in msg.walk():
			content_type = part.get_content_type()
			if content_type == 'text/html':
				html_content = part.get_payload(decode=True).decode('utf-8', errors='ignore')
			elif content_type == 'text/plain' and not plain_content:
				plain_content = part.get_payload(decode=True).decode('utf-8', errors='ignore')
	else:
		content_type = msg.get_content_type()
		payload = msg.get_payload(decode=True)
		if payload:
			decoded = payload.decode('utf-8', errors='ignore')
			if content_type == 'text/html':
				html_content = decoded
			else:
				plain_content = decoded
	
	# Create SendGrid mail object
	if html_content:
		content = Content("text/html", html_content)
	elif plain_content:
		content = Content("text/plain", plain_content)
	else:
		content = Content("text/plain", "No content")
	
	mail = Mail(from_email, to_email, subject, content)
	
	# Add CC if present
	if msg.get('CC'):
		cc_list = msg.get('CC').split(',')
		for cc in cc_list:
			mail.add_cc(cc.strip())
	
	# Add BCC if present
	if msg.get('BCC'):
		bcc_list = msg.get('BCC').split(',')
		for bcc in bcc_list:
			mail.add_bcc(bcc.strip())
	
	# Add Reply-To if present
	if msg.get('Reply-To'):
		mail.reply_to = msg.get('Reply-To')
	
	# Send via SendGrid
	sg = SendGridAPIClient(api_key)
	response = sg.send(mail)
	
	# Log success
	frappe.logger().info(f"SendGrid API email sent to {recipient}. Status: {response.status_code}")
	
	if response.status_code not in [200, 201, 202]:
		frappe.throw(_(
			"SendGrid API returned status code: {0}. Response: {1}"
		).format(response.status_code, response.body))

