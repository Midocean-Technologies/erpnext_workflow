
import frappe
from frappe.model.document import Document
from erpnext_workflow.mobile_api.fcm_notification import triggerd_fcm_notification
import requests
import json

class SocketNotificationList(Document):
	def after_insert(self):
		# frappe.enqueue("erpnext_workflow.erpnext_workflow.doctype.socket_notification_list.socket_notification_list.send_fcm_notification",doc=self, queue='long')
		frappe.enqueue("erpnext_workflow.erpnext_workflow.doctype.socket_notification_list.socket_notification_list.send_notification_data",doc=self, queue='long')

@frappe.whitelist()
def send_fcm_notification(doc):
	try:
		if doc.user:
			user_fcm_token = frappe.get_value("User", doc.user, 'user_fcm_token')
			if user_fcm_token:
				if doc.notification_from == "Comment":
					title = 'Comment From {0}'.format(doc.comment_by)
				else:
					title = 'Workflow Action Requered !'
				triggerd_fcm_notification(user_fcm_token, title, doc.message, doc.json)

	except Exception as e:
		frappe.log_error("FCM Notification Error", frappe.get_traceback(e))


@frappe.whitelist()
def send_notification_data(doc):
	try:
		
		url = "https://midocean.frappe.cloud/api/method/erp_notification.mobile_api.create_notification"
		# url = "https://94f5771fa1f6542b-117-222-237-191.serveousercontent.com/api/method/erp_notification.mobile_api.create_notification"
		
		headers = {
		'Content-Type': 'application/json',
		}
		params =json.dumps({
			'doctype_' : doc.doctype_,
			'doctype_id' : doc.doctype_id,
			'user' : doc.user,
			'workflow_state' : doc.workflow_state,
			'notification_from' : doc.notification_from,
			'comment_by' : doc.comment_by,
			'seen' : doc.seen,
			'message' : doc.message,
			'json' : doc.json,
		})
		
		response = requests.request("POST", url, headers=headers, data=params)
  
	except Exception as e:
		frappe.log_error(frappe.get_traceback(e), "Socket Notification Error")