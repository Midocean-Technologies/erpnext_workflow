import frappe
from frappe.auth import LoginManager
from frappe import _
from erpnext_workflow.mobile_api.v1.api_utils import * 
from frappe.model.workflow import get_transitions, get_workflow, apply_workflow
import re
from frappe.utils.user import get_users_with_role
from frappe.workflow.doctype.workflow_action.workflow_action import create_workflow_actions_for_roles, is_workflow_action_already_created

# At the workflow step whose transition condition uses this field (e.g. `frappe.session.user == doc.leave_approver`),
# only that user gets the notification and sees the document in the mobile app
APPROVER_FIELDS = {"Expense Claim": "expense_approver", "Leave Application": "leave_approver"}


def mobile_app_workflow_filters():
    """Workflows are used in the mobile app only when "Send Mobile App Notification" is ticked"""
    filters = {"is_active": 1}
    if frappe.get_meta("Workflow").has_field("send_mobile_app_notification"):
        filters["send_mobile_app_notification"] = 1
    return filters


def is_approver_step(doctype, workflow_name, state):
    field = APPROVER_FIELDS.get(doctype)
    return bool(field and frappe.db.exists("Workflow Transition", {"parent": workflow_name, "state": state, "condition": ["like", f"%{field}%"]}))


def is_hidden_for_user(doctype, name):
    """In the mobile app lists, a document at the approver step is shown only to its approver"""
    if doctype not in APPROVER_FIELDS:
        return False
    workflow = get_workflow(doctype)
    state, approver = frappe.db.get_value(doctype, name, [workflow.workflow_state_field, APPROVER_FIELDS[doctype]]) or (None, None)
    return is_approver_step(doctype, workflow.name, state) and approver != frappe.session.user


def get_frappe_version() -> str:
    return getattr(frappe, "__version__", "unknown")

@frappe.whitelist(allow_guest=True)
def login(usr, pwd):
    try:
        login_manager = LoginManager()
        login_manager.authenticate(usr, pwd)
        login_manager.post_login()

        frappe_version = get_frappe_version()

        if frappe.response.get("message") == "Logged In":
            user = login_manager.user

            roles = frappe.get_roles(user)
            if "Workflow Mobile App" not in roles:
                frappe.throw(
                    "You don't have permission for Workflow Mobile App. Please contact Administrator."
                )

            try:
                settings = frappe.get_single("Smart Workflow Settings")
            except frappe.DoesNotExistError:
                frappe.throw(
                    "You don't have permission for Workflow Mobile App. Please contact Administrator."
                )

            if not settings.enabled:
                frappe.throw(
                    "You don't have permission for Workflow Mobile App. Please contact Administrator."
                )

            return gen_response(
                200,
                "Logged In",
                {
                    "user": user,
                    "frappe_version": frappe_version
                }
            )

        return gen_response(500, "Login failed")

    except frappe.AuthenticationError:
        return gen_response(500, "Invalid username or password")

    except Exception as e:
        clean_msg = BeautifulSoup(str(e), "lxml").get_text()
        return gen_response(500, clean_msg)

@frappe.whitelist()
@mtpl_validate(methods=["GET"])
def get_document_type_list(user=None):
    try:
        active_workflows = frappe.get_all(
            "Workflow",
            filters=mobile_app_workflow_filters(),
            fields=["document_type"]
        )

        workflow_doctypes = {w.document_type for w in active_workflows}

        doc = frappe.get_list(
            "Workflow Action",
            filters={
                "status": "Open",
                "reference_doctype": ["in", list(workflow_doctypes)]
            },
            fields=["name", "reference_name", "reference_doctype"]
        )
        doc = [d for d in doc if not is_hidden_for_user(d.reference_doctype, d.reference_name)]

        return gen_response(200, "Data Fetch Successfully", doc)

    except frappe.PermissionError:
        return gen_response(500, "Not permitted")

    except Exception as e:
        return exception_handler(e)

@frappe.whitelist()
@mtpl_validate(methods=["GET"])
def get_document_list(reference_doctype, start ,  page_length, reference_name = None, title=None, user=None):
    try:
        lst = []
        settings = frappe.get_single("Smart Workflow Settings")

        if not frappe.db.exists("Workflow", {"document_type": reference_doctype, **mobile_app_workflow_filters()}):
            return gen_response(200, "Data Fetched Successfully", lst)

        workflow_state_filter = frappe.form_dict.get("workflow_state")

        filters = {
            "status": "Open",
            "reference_doctype": reference_doctype,
        }

        if reference_name:
            filters["reference_name"] = ("like", f"%{reference_name}%")

            
        document_list = []   
        document_list_1 = frappe.get_list(
            "Workflow Action",
            filters=filters,
            page_length=page_length,
            start=start,
            fields=["name", "reference_name", "reference_doctype"]
        )
        for d1 in document_list_1:
            document_list.append(d1)
        
        ref_doc_meta = frappe.get_meta(reference_doctype)
        if ref_doc_meta.get("title_field") and title: 
            ref_doctype_list = frappe.get_list(reference_doctype, filters={ref_doc_meta.get("title_field"): ("like", f"%{title}%")})
            x = []
            for i in ref_doctype_list:
                x.append(i.name)
            filters["reference_name"] = ['in', x]
            
            
            document_list_2 = frappe.get_list(
            "Workflow Action",
            filters=filters,
            page_length=page_length,
            start=start,
            fields=["name", "reference_name", "reference_doctype"])
            for d2 in document_list_2:
                if d2 not in document_list:
                    document_list.append(d2)
        
        
        workflow_name = frappe.db.get_value(
            "Workflow",
            {"document_type": reference_doctype, "is_active": 1},
            "name"
        )
 
        workflow_state_field = "workflow_state"
        if workflow_name:
            workflow_state_field = frappe.db.get_value(
                "Workflow",
                workflow_name,
                "workflow_state_field"
            ) or "workflow_state"
 
        meta = frappe.get_meta(reference_doctype)
        title_field = meta.title_field
 
        for row in document_list:
            if not frappe.db.exists(row.reference_doctype, row.reference_name) or is_hidden_for_user(row.reference_doctype, row.reference_name):
                continue

            doc = frappe.get_doc(row.reference_doctype, row.reference_name)
            
            current_state = getattr(doc, workflow_state_field, "")
            if workflow_state_filter and current_state != workflow_state_filter:
                continue
 
            info = {
                "reference_doctype": row.reference_doctype,
                "reference_name": row.reference_name,
                "workflow_state": current_state,
                "title": doc.get(title_field) if title_field else row.reference_name
            }
 
            lst.append(info)
 
        return gen_response(200, "Data Fetched Successfully", lst)
 
    except frappe.PermissionError:
        return gen_response(500, "Not permitted")
 
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "get_document_list Error")
        return gen_response(500, "Something went wrong")


@frappe.whitelist()
def get_existing_document_list():
    try:
        result = {}

        workflow_list = frappe.get_all("Workflow", filters={'is_active': 1}, fields=['document_type'])
        for i in workflow_list:
            doctype = i.document_type
            result.setdefault(doctype, [])
            records = frappe.get_all(doctype, filters={"docstatus": 0}, fields=["name",'workflow_state'],limit=1000)
            for doc in records:
                exists = frappe.db.exists("Workflow Action",{"reference_doctype": doctype, "reference_name": doc.name})
                if not exists:
                    wa = frappe.get_doc({
                        "doctype": "Workflow Action",
                        "reference_doctype": doctype,
                        "reference_name": doc.name,
                        "workflow_state": doc.workflow_state,
                        "status": "Open"
                    })
                    wa.insert(ignore_permissions=True)

                result[doctype].append({
                    "name": doc.name,
                })
        return result

    except Exception as e:
        frappe.log_error(frappe.get_traceback(e), "get_existing_document_list Error")
        return []


def get_status(status):
	if status == 0:
		return 'Draft'

	if status == 1:
		return 'Submitted'
	
	if status == 2:
		return 'Cancelled'
    
@frappe.whitelist()
@mtpl_validate(methods=["GET"])
def get_document_list_5_record(user=None):
    try:
        lst = []
	
        workflow_doctypes = frappe.get_all("Workflow", filters=mobile_app_workflow_filters(), pluck="document_type")
        document_list = frappe.get_list('Workflow Action', filters={'status': 'Open', 'reference_doctype': ['in', workflow_doctypes]}, fields=['name', 'reference_name', 'reference_doctype'], limit_page_length=5)
        for row in document_list:
            docc = {}
            if frappe.db.exists(row.reference_doctype, row.reference_name) and not is_hidden_for_user(row.reference_doctype, row.reference_name):
                doc = frappe.get_doc(row.reference_doctype, row.reference_name)
                docc['reference_doctype'] = row.reference_doctype
                docc['reference_name'] = row.reference_name
                docc['workflow_state'] = doc.get("workflow_state")
                docc['title'] = doc.get(doc.meta.title_field or "title") or doc.name
                docc['status'] = get_status(doc.docstatus)
                lst.append(docc)
        gen_response(200 ,"Data Fetch Succesfully", lst)
    except frappe.PermissionError:
        return gen_response(500, "Not permitted")
    except Exception as e:
        return exception_handler(e)

@frappe.whitelist()
@mtpl_validate(methods=["GET"])
def get_workflow_action(reference_doctype, reference_name):
    try:
        doc = frappe.get_doc(reference_doctype, reference_name)
        workflow = get_workflow(doc.doctype)
        data = get_transitions(doc, workflow)
        gen_response(200 ,"Data Fetch Succesfully", data)
    except frappe.PermissionError:
        return gen_response(500, "Not permitted")
    except Exception as e:
        return exception_handler(e)

@frappe.whitelist()
@mtpl_validate(methods=["GET"])
def get_print_format(reference_doctype, reference_name):
    try:
        print_format_name = "Standard"
        workflow_list = frappe.get_all("Workflow",filters={'document_type': reference_doctype, 'is_active': 1}, fields=['print_format'])
        for i in workflow_list:
            if i.print_format:
                print_format_name = i.print_format
        
        # if not print_format_name:
        #     print_format_name = "Standard"
        
        res = frappe.get_print(doctype=reference_doctype, name=reference_name, print_format=print_format_name)
        
        # Replace grey background
        res = res.replace('background-color: #d1d8dd;', 'background-color: white;')
        res = res.replace('padding: 30px 0px;', 'padding: 0px;')
        
        # Remove unwanted patterns
        unwanted_patterns = [
            r'<div class="action-banner print-hide">.*?</div>',  
        ]
        for pattern in unwanted_patterns:
            res = re.sub(pattern, '', res, flags=re.DOTALL)
        
        res = re.sub(r'<link[^>]*print\.bundle[^>]*>', '', res)
        
        alignment_css = """
        <style>
        .text-right { text-align: right !important; }
        .text-center { text-align: center !important; }
        .text-left { text-align: left !important; }
        
        .print-format { max-width: 8.3in; margin: 0 auto; padding: 15px; }
        table { width: 100%; border-collapse: collapse; }
        table.table-bordered { border: 1px solid #d1d8dd; }
        table.table-bordered td, table.table-bordered th { 
            border: 1px solid #d1d8dd; 
            padding: 8px;
        }
        .col-xs-1 { width: 8.33%; }
        .col-xs-2 { width: 16.66%; }
        .col-xs-3 { width: 25%; }
        .col-xs-4 { width: 33.33%; }
        .col-xs-5 { width: 41.66%; }
        .col-xs-6 { width: 50%; }
        .col-xs-7 { width: 58.33%; }
        .col-xs-8 { width: 66.66%; }
        .col-xs-9 { width: 75%; }
        .col-xs-10 { width: 83.33%; }
        .col-xs-11 { width: 91.66%; }
        .col-xs-12 { width: 100%; }
        .row { display: flex; flex-wrap: wrap; }
        .row > div { float: left; }
        </style>
        """
        
        res = res.replace('</head>', alignment_css + '</head>')
            
        return gen_response(200, "Data Fetched Successfully", res)
        
    except frappe.PermissionError:
        return gen_response(403, "Not permitted")
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Print Format Error")
        return exception_handler(e)


@frappe.whitelist()
@mtpl_validate(methods=["POST"])
def update_workflow(reference_doctype, reference_name, action):
    try:
        # doc = get_doc_details(reference_doctype, reference_name)
        doc = frappe.get_doc(reference_doctype, reference_name)
        apply_workflow(doc, action)
        gen_response(200 ,"Workflow Updated")
    except frappe.PermissionError:
        return gen_response(500, "Not permitted")
    except Exception as e:
        return exception_handler(e)

@frappe.whitelist()
def store_fcm_token(user, token):
    try:
        doc = frappe.get_doc('User', user)
        doc.db_set('user_fcm_token', token)
        frappe.db.commit()
        return doc
    except Exception as e:
        raise e

# @frappe.whitelist()
# @mtpl_validate(methods=["POST"])
def trigger_workflow_notification(doc, method):
    
    if doc.doctype == "Comment":
        try:
            if doc.comment_type == "Comment":
                current_user = frappe.session.user  
                
                soup1 = BeautifulSoup(doc.content, "html.parser")
                content = soup1.get_text()
                
                message = {
                    "owner": current_user,
                    "comment_type": "Comment",
                    "comment_email": doc.comment_email,
                    "comment_by": doc.comment_by,
                    "reference_doctype": doc.reference_doctype,
                    "reference_name": doc.reference_name,
                    "content": content,
                }
                workflow_name = frappe.db.get_value("Workflow",{"document_type": doc.reference_doctype, **mobile_app_workflow_filters()},"name")
                if not workflow_name:
                    return

                workflow_state_field = frappe.db.get_value("Workflow",workflow_name,"workflow_state_field")
                if not workflow_state_field:
                    return

                ref_doc = frappe.get_doc(doc.reference_doctype, doc.reference_name)
                current_state = ref_doc.get(workflow_state_field)
                if not current_state:
                    return

                current_role = frappe.db.get_value("Workflow Document State",{"parent": workflow_name,"state": current_state},"allow_edit")
                if not current_role:
                    return

                users = frappe.db.get_all("Has Role",filters={"role": current_role},fields=["parent as user"])

                enabled_users = [u.user for u in users if frappe.db.get_value("User", u.user, "enabled") and u.user != current_user]
                if is_approver_step(doc.reference_doctype, workflow_name, current_state):
                    enabled_users = [u for u in enabled_users if u == ref_doc.get(APPROVER_FIELDS[doc.reference_doctype])]
                if not enabled_users:
                    return

                for user in enabled_users:
                    frappe.publish_realtime(event="comment_notification",message=message,user=user)
                
                msg_str = f"{content} \n{doc.reference_doctype} ({doc.reference_name})"   
                for user in enabled_users:
                    try:
                        nl = frappe.new_doc("Socket Notification List")
                        nl.user = user
                        nl.seen = 0
                        nl.doctype_ = doc.reference_doctype
                        nl.doctype_id = doc.reference_name
                        nl.message = str(msg_str)
                        nl.json = str(message)
                        nl.notification_from = 'Comment'
                        nl.comment_by = doc.comment_by
                        nl.save(ignore_permissions=True)
                    except Exception as e:
                        frappe.log_error(f"Error creating Socket Notification for {user}: {str(e)}")
                return message


        except Exception:
            frappe.log_error(frappe.get_traceback(), "Comment Notification Error")
            return
        
    
    workflow_name = frappe.db.get_value("Workflow",{"document_type": doc.doctype, **mobile_app_workflow_filters()}, "name")
    if not workflow_name:
        return

    workflow_state_field = frappe.db.get_value("Workflow",workflow_name,"workflow_state_field")
    if not workflow_state_field:
        return
    
    new_state = doc.get(workflow_state_field)
    previous = doc.get_doc_before_save()
    old_state = previous.get(workflow_state_field) if previous else None
    
    if not new_state or old_state == new_state:
        return

    approver_step = is_approver_step(doc.doctype, workflow_name, new_state)
    if approver_step and not is_workflow_action_already_created(doc):
        # Frappe checks the approver condition as the user who moved the document (e.g. the employee), so it creates
        # no Workflow Action for this step. Create it, so the approver sees the document in the mobile app lists.
        create_workflow_actions_for_roles({t.allowed for t in get_workflow(doc.doctype).transitions if t.state == new_state}, doc)

    current_role = frappe.db.get_value("Workflow Document State",{"parent": workflow_name, "state": new_state},"allow_edit")
    if not current_role:
        return

    users = frappe.db.get_all("Has Role",filters={"role": current_role},fields=["parent as user"])
    enabled_users = [u.user for u in users if frappe.db.get_value("User", u.user, "enabled")]
    if approver_step:
        enabled_users = [u for u in enabled_users if u == doc.get(APPROVER_FIELDS[doc.doctype])]
    if not enabled_users:
        return

    transitions = frappe.get_all("Workflow Transition",filters={"parent": workflow_name, "state": new_state},fields=["action"])
    actions_list = [{"action": t["action"]} for t in transitions]

    ref_doc = frappe.get_doc(doc.doctype, doc.name)
    message = {
        "doctype": doc.doctype,
        "docname": doc.name,
        "msg": new_state,
        "actions": actions_list,
    }
        
    for user in enabled_users:
        frappe.publish_realtime("erp_notification", message, user=user)
    
    
    msg_str = f"{doc.doctype} ({doc.name})\n{ref_doc.workflow_state}"

    title_field = ref_doc.meta.title_field
    if title_field and ref_doc.get(title_field):
        msg_str += f"\n{ref_doc.get(title_field)}"
        
    for user in enabled_users:
        try:
            nl = frappe.new_doc("Socket Notification List")
            nl.user = user
            nl.seen = 0
            nl.doctype_ = doc.doctype
            nl.doctype_id = doc.name
            nl.workflow_state = new_state
            nl.message = str(msg_str)
            nl.json = str(message)
            nl.notification_from = 'WorkFlow Action'
            nl.save(ignore_permissions=True)
        except Exception as e:
            frappe.log_error(f"Error creating Socket Notification for {user}: {str(e)}")

    frappe.db.commit()
    return message
    
