/** @odoo-module **/

import {registry} from "@web/core/registry";
import {X2ManyField} from "@web/views/fields/x2many/x2many_field";
import {useOpenX2ManyRecord, useX2ManyCrud} from "@web/views/fields/relational_utils";
import {AutomationKanbanRenderer} from "../views/automation_kanban/automation_kanban_renderer.esm";

export class AutomationActivity extends X2ManyField {
    setup() {
        super.setup();
        const {saveRecord, updateRecord} = useX2ManyCrud(
            () => this.list,
            this.isMany2Many
        );
        const openRecord = useOpenX2ManyRecord({
            resModel: this.list.resModel,
            activeField: this.activeField,
            activeActions: this.activeActions,
            getList: () => this.list,
            saveRecord: async (record) => {
                await saveRecord(record);
                await this.props.record.save();
            },
            updateRecord,
            withParentId: this.activeField.widget !== "many2many",
        });
        this._openRecord = (params) => {
            const activeElement = document.activeElement;
            openRecord({
                ...params,
                onClose: () => {
                    if (activeElement) {
                        activeElement.focus();
                    }
                },
            });
        };
    }
}

AutomationActivity.components = {
    ...AutomationActivity.components,
    KanbanRenderer: AutomationKanbanRenderer,
};

registry.category("fields").add("automation_activity", AutomationActivity);
