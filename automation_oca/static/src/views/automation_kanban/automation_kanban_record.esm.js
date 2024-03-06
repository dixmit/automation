/** @odoo-module */

import {KanbanRecord} from "@web/views/kanban/kanban_record";

export class AutomationKanbanRecord extends KanbanRecord {
    addNewChild(params) {
        this.env.onAddActivity({
            context: {
                default_parent_id: this.props.record.data.id,
                default_trigger_type: params.trigger_type,
            },
        });
    }
}
