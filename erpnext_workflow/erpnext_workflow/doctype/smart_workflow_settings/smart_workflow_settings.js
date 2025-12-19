// Copyright (c) 2025, Midocean Technologies Pvt Ltd and contributors
// For license information, please see license.txt

// frappe.ui.form.on("Smart Workflow Settings", {
// 	refresh(frm) {

// 	},
// });
frappe.ui.form.on('Smart Workflow Settings', {
    onload: function (frm) {
        if (!frm.doc.enabled) {
            frm.set_value('enabled', 1);
            frm.save();
        }
    }
});
