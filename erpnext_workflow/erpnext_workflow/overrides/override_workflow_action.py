import frappe
# from frappe import _
# from frappe.email.doctype.email_template.email_template import get_email_template
# from frappe.model.document import Document
# from frappe.workflow.doctype.workflow_action.workflow_action import WorkflowAction
from frappe.workflow.doctype.workflow_action.workflow_action import *

# class CustomWorkflowAction(WorkflowAction):


def process_workflow_actions(doc, state):
    # print("************method calling****************")
    workflow = get_workflow_name(doc.get("doctype"))
    if not workflow:
        return

    if state == "on_trash":
        clear_workflow_actions(doc.get("doctype"), doc.get("name"))
        return

    if is_workflow_action_already_created(doc):
        return

    update_completed_workflow_actions(doc, workflow=workflow, workflow_state=get_doc_workflow_state(doc))
    clear_doctype_notifications("Workflow Action")

    next_possible_transitions = get_next_possible_transitions(workflow, get_doc_workflow_state(doc), doc)

    if not next_possible_transitions:
        return

    roles = {t.allowed for t in next_possible_transitions}
    create_workflow_actions_for_roles(roles, doc)

    if send_email_alert(workflow) and frappe.db.get_value(
        "Workflow Document State",
        filters={"parent": workflow, "state": get_doc_workflow_state(doc)},
        fieldname="send_email",
    ):
        enqueue(
            send_workflow_action_email,
            queue="short",
            doc=doc,
            transitions=next_possible_transitions,
            enqueue_after_commit=True,
            now=frappe.flags.in_test,
        )
    workflow_name = get_workflow_name(doc.get("doctype"))

    send_mobile_app_notification= frappe.db.get_value('Workflow',workflow_name,'send_mobile_app_notification')
    
    if send_mobile_app_notification:
        message = {
            "doctype": workflow_name,
            "docname": doc.name,
            "msg": doc.workflow_state,
            "actions" : [{"action": t.action} for t in next_possible_transitions],
        }
        frappe.log_error("Workflow Notification", message)
        try:
            # frappe.publish_realtime("erp_notification", message)
            frappe.publish_realtime("erp_notification", {"msg": message})

        except Exception as e:
            frappe.log_error(f"Failed to send workflow notification for {doc.doctype} {doc.name}", str(e))

