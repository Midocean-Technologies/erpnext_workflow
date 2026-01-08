# Copyright (c) 2025, Midocean Technologies Pvt Ltd and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from erpnext_workflow.mobile_api.fcm_notification import triggerd_fcm_notification

class SocketNotificationList(Document):
	def after_insert(self):
		try:
			if self.user:
				user_fcm_token = frappe.get_value("User", self.user, 'user_fcm_token')
				triggerd_fcm_notification(user_fcm_token, self.doctype_, self.doctype_id)
    
		except Exception as e:
			frappe.log_error("FCM Notification Error", frappe.get_traceback(e))

      
            
	
