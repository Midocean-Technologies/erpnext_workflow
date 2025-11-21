__version__ = "0.0.1"

from frappe.workflow.doctype.workflow_action import workflow_action
from erpnext_workflow.erpnext_workflow.overrides import override_workflow_action

workflow_action.process_workflow_actions = override_workflow_action.process_workflow_actions