/** @odoo-module **/

import {ComponentWrapper} from "web.OwlCompatibility";
import AbstractAction from "web.AbstractAction";
import core from "web.core";
import {Component, useState, useRef, onMounted, xml} from "@odoo/owl";

export class DraggableItem extends Component {
    setup() {
        this.state = useState({position_x: 100, position_y: 100});
        this.isDragging = false;
        this.boxRef = useRef("box");

        onMounted(() => {
            this.box = this.boxRef.el;
            this.box.addEventListener("mousedown", this.startDrag);
            document.addEventListener("mousemove", this.onDrag);
            document.addEventListener("mouseup", this.stopDrag);
        });
    }

    startDrag = (event) => {
        this.isDragging = true;
        this.offsetX = event.clientX - this.state.position_x;
        this.offsetY = event.clientY - this.state.position_y;
    };

    onDrag = (event) => {
        if (!this.isDragging) return;
        this.state.position_xx = event.clientX - this.offsetX;
        this.state.position_y = event.clientY - this.offsetY;
    };

    stopDrag = () => {
        this.isDragging = false;
    };

    willUnmount() {
        document.removeEventListener("mousemove", this.onDrag);
        document.removeEventListener("mouseup", this.stopDrag);
    }
}

DraggableItem.template = "automation_flowchart.FlowchartItem";

export class ActionFlowchart extends Component {
    setup() {
        super.setup(...arguments);
        this.iframe = useRef("flowchart_iframe");
        this.actionService = this.props.actionService;
        // onMounted(this.insertBoxes.bind(this));
        this.boxes = [
            {top: "50px", left: "100px", width: "100px", height: "50px", color: "red"},
        ];
    }

    insertBoxes() {
        const iframeDoc = this.iframe.el.contentDocument;
        if (!iframeDoc) return;
        iframeDoc.body.style.position = "relative";

        const boxes = [
            {top: "50px", left: "100px", width: "100px", height: "50px", color: "red"},
            {
                top: "150px",
                left: "700px",
                width: "250px",
                height: "30px",
                color: "blue",
            },
            {
                top: "100px",
                left: "300px",
                width: "80px",
                height: "400px",
                color: "green",
            },
        ];

        boxes.forEach((box) => {
            let div = iframeDoc.createElement("div");
            div.style.position = "absolute";
            div.style.top = box.top;
            div.style.left = box.left;
            div.style.width = box.width;
            div.style.height = box.height;
            div.style.backgroundColor = box.color;
            div.style.border = "1px solid black";
            iframeDoc.body.appendChild(div);
        });
    }

    goBack() {
        console.error("Not implemented yet.");
        return;

        this.actionService.doAction({
            type: "ir.actions.act_window",
            res_model: "automation.flowchart",
            res_id: this.props.res_id,
            views: [[false, "form"]],
            target: "current",
        });
    }
}

ActionFlowchart.components = {DraggableItem};
ActionFlowchart.template = "automation_flowchart.ActionFlowchart";

export const AutomationFlowchartAction = AbstractAction.extend({
    async start() {
        await this._super.apply(this, arguments);

        this.component = new ComponentWrapper(this, ActionFlowchart, {
            res_id: this.res_id,
            actionService: this,
        });
        return this.component.mount(this.$(".o_content")[0]);
    },
});

core.action_registry.add("action_automation_flowchart", AutomationFlowchartAction);
