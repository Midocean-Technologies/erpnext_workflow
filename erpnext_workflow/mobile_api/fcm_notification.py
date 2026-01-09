import json
import os
from pyfcm import FCMNotification
import frappe
from google.oauth2 import service_account

def triggerd_fcm_notification(fcm_token,title, body, image=None):
    
    fcm_json_data = frappe.get_doc("Smart Workflow Settings","Smart Workflow Settings")
    
    # gcp_json_credentials_dict = json.loads(os.getenv('/Users/anjukakran/Documents/Erpnext/V14/frappe-bench/apps/erpnext_workflow/erpnext_workflow/mobile_api/data.json' , None))
    gcp_json_credentials_dict = json.loads(fcm_json_data.fcm_json_data)
    credentials = service_account.Credentials.from_service_account_info(gcp_json_credentials_dict, scopes=['https://www.googleapis.com/auth/firebase.messaging'])
    fcm = FCMNotification(service_account_file=None, credentials=credentials, project_id="erpnext-workflow-c5727")

    fcm_token = fcm_token
    notification_title = title
    notification_body = body
    notification_image = image
    result = fcm.notify(fcm_token=fcm_token, notification_title=notification_title, notification_body=notification_body, notification_image=notification_image)