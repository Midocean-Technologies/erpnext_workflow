
import frappe
from frappe.model.document import Document
from erpnext_workflow.mobile_api.fcm_notification import triggerd_fcm_notification

class SocketNotificationList(Document):
	def after_insert(self):
		frappe.enqueue("erpnext_workflow.erpnext_workflow.doctype.socket_notification_list.socket_notification_list.send_fcm_notification",doc=self, queue='long')

@frappe.whitelist()
def send_fcm_notification(doc):
	try:
		if doc.user:
			user_fcm_token = frappe.get_value("User", doc.user, 'user_fcm_token')
			if user_fcm_token:
				triggerd_fcm_notification(user_fcm_token, doc.doctype_, doc.doctype_id)
				# triggerd_fcm_notification(user_fcm_token, 'WorkFlow Action Updated', doc.message)

	except Exception as e:
		frappe.log_error("FCM Notification Error", frappe.get_traceback(e))


