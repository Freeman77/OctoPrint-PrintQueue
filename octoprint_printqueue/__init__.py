# coding=utf-8
from __future__ import absolute_import

import octoprint.plugin
import octoprint.filemanager
from flask import jsonify, request, make_response
import os
from octoprint_printqueue.printqueue import PrintQueue
#import RPi.GPIO as GPIO
#import time


class PrintQueuePlugin(octoprint.plugin.StartupPlugin,
                       octoprint.plugin.TemplatePlugin,
                       octoprint.plugin.SettingsPlugin,
                       octoprint.plugin.EventHandlerPlugin,
                       octoprint.plugin.BlueprintPlugin,
                       octoprint.plugin.AssetPlugin):

    def __init__(self):
        self._printqueue_db_path = None
        self._printq_datamodel = None
        self.led = None
        self.button = None
        self.current_item = None


    # -- StartupPlugin mixin --
    def on_after_startup(self):
        self._printqueue_db_path = os.path.join(self.get_plugin_data_folder(), "printqueue.db")
        self._printq_datamodel = PrintQueue(self._printqueue_db_path)
        self._printq_datamodel.status = "stopped"
        #self.init_physical()

    def init_physical(self):
        pass
        # GPIO.setmode(GPIO.BOARD)
        # GPIO.setup(self.led, GPIO.OUT)
        # GPIO.setup(self.button, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        # GPIO.add_event_detect(self.button, GPIO.RISING, callback=self.on_button, bouncetime=1000)

    def update_physical(self, status):
        pass
        # if status == 'paused':
        #     self._blink()
        # elif status == 'running':
        #     GPIO.output(self.led, True)
        # else:
        #     GPIO.output(self.led, False)

    def _blink(self):
        pass
        # GPIO.output(self.led, True)
        # time.sleep(1)
        # GPIO.output(self.led, False)
        # time.sleep(1)

    def on_button(self):
        pass
        # if self._printq_datamodel.status in ('paused', 'stopped'):
        #     self.sync(
        #         self._printq_datamodel.status('running')
        #     )

    def sync(self, command):
        if self._printq_datamodel.status in ('stopped', 'paused') and command == 'start':
            #start printing first element in queue
            self.print_item(printAfterSelect=True)

        elif self._printq_datamodel.status == 'running' and command == 'stop':
            self.print_item(printAfterSelect=False)
        self._printq_datamodel.status = command
        #self.update_physical(new_status)


    def print_item(self, printAfterSelect=True):
        item = self._printq_datamodel.current_item
        if item and self._printer.is_ready():
            self._printer.select_file(
                self._file_manager.path_on_disk('local', item['filename']),
                printAfterSelect=printAfterSelect,
                sd=False
            )

    # -- EventHandlerPlugin mixin
    def on_event(self, event, payload):
        if event in ('PrintFailed', 'PrintCancelled'):
            self.on_print_failed()
        elif event in ('PrintDone'):
            self.on_print_finished()
        elif event in ('PrintStarted'):
            self.on_print_started()

    def on_print_failed(self):
        self.sync('stopped')

    def on_print_finished(self):
        if self._printq_datamodel.status == 'running':
            self.sync('paused')

    def on_print_started(self):
        if self._printq_datamodel.status == 'paused':
            self.sync('running')
        else: #someone else started a non-queue item
            self.sync('stopped')


    # -- SettingsPlugin mixin --
    def get_settings_defaults(self):
        return {
            # RPI button and led pins
            'button_pin': 4,
            'led_pin': 17
        }

    # -- BlueprintPlugin mixin --
    @octoprint.plugin.BlueprintPlugin.route("/queue", methods=["GET"])
    def api_get_printqueue_items(self):
        return jsonify(q_status=self._printq_datamodel.status, queue_items=self._printq_datamodel.get_queue_items())

    @octoprint.plugin.BlueprintPlugin.route("/queue/items", methods=["POST"])
    def api_add_queueitem(self):
        from werkzeug.exceptions import BadRequest

        try:
            json_data = request.json
        except BadRequest:
            return make_response("Malformed JSON body in request", 400)

        if not "filename" in json_data:
            return make_response("Missing filename in request", 400)
        if not "total_copies" in json_data:
            return make_response("Missing total_copies in request", 400)

        filename = json_data["filename"]
        total_copies = json_data["total_copies"]
        notes = json_data["notes"]
        if 0 < total_copies < 100:
            if self._printq_datamodel.add_queue_item(filename, total_copies, notes):
                return jsonify({"status": "ok"})
            else:
                return jsonify({"status": "failed"})
        else:
            return jsonify({"status": "failed", "message": "total_copies must be in range 0<x<100"})

    @octoprint.plugin.BlueprintPlugin.route("/queue/items", methods=["PUT"])
    def api_upd_queueitem(self):
        from werkzeug.exceptions import BadRequest
        try:
            json_data = request.json
        except BadRequest:
            return make_response("Malformed JSON body in request", 400)
        if not "q_id" in json_data:
            return make_response("Missing q_id in request", 400)

        q_id = json_data["q_id"]
        item_to_mod = self._printq_datamodel.get_queue_item_by_id(q_id)

        total_copies = json_data["total_copies"] if "total_copies" in json_data else item_to_mod["total_copies"]
        notes = json_data["notes"] if "notes" in json_data else item_to_mod["notes"]

        if item_to_mod:
            if total_copies >= item_to_mod['printed_copies'] and total_copies > 0:
                if self._printq_datamodel.upd_queue_item(q_id, total_copies, notes):
                    return jsonify({"status": "ok"})
                else:
                    return jsonify({"status": "failed"})
            else:
                return jsonify({"status": "failed", "message": "total_copies can't be less than printed_copies amount or zero"})
        else:
            return jsonify({"status": "failed", "message": "q_id not found"})

    @octoprint.plugin.BlueprintPlugin.route("/queue/items/<int:q_id>", methods=["DELETE"])
    def api_rem_queueitem(self, q_id):
        if self._printq_datamodel.rem_queue_item(q_id):
            return jsonify({"status": "ok"})
        else:
            return jsonify({"status": "failed"})

    @octoprint.plugin.BlueprintPlugin.route("/queue/items/priority", methods=["POST"])
    def api_change_priority(self):
        from werkzeug.exceptions import BadRequest
        try:
            json_data = request.json
        except BadRequest:
            return make_response("Malformed JSON body in request", 400)
        if not "q_id" in json_data:
            return make_response("Missing 'q_id' in request", 400)
        if not "move" in json_data:
                return make_response("Missing 'move' in request", 400)

        q_id = json_data["q_id"]
        move = json_data["move"]

        if move in ("up", "down"):
            if self._printq_datamodel.change_priority(q_id, move):
                return jsonify({"status": "ok"})
            else:
                return jsonify({"status": "failed"})

    @octoprint.plugin.BlueprintPlugin.route("/queue", methods=["POST"])
    def api_queue_action(self):
        from werkzeug.exceptions import BadRequest
        try:
            json_data = request.json
        except BadRequest:
            return make_response("Malformed JSON body in request", 400)
        if not "command" in json_data:
            return make_response("Missing 'command' in request", 400)

        command = json_data["command"]

        if command in ("start", "stop"):
            self.sync(command)
            status = self._printq_datamodel.status
            return jsonify({"status": status})

    # -- Template mixin --
    def get_template_configs(self):
        return [
            dict(type="tab", name="Queue")
        ]

    # -- Assets mixin --
    def get_assets(self):
        return dict(
            js=["js/printqueue.js"],
            css=["css/printqueue.css"],
            less=["less/printqueue.less"]
        )

    def get_update_information(self):
        # Define the configuration for your plugin to use with the Software Update
        # Plugin here. See https://github.com/foosel/OctoPrint/wiki/Plugin:-Software-Update
        # for details.
        return dict(
            printqueue=dict(
                displayName="Print Queue",
                displayVersion=self._plugin_version,

                # version check: github repository
                type="github_release",
                user="Freeman77",
                repo="OctoPrint-PrintQueue",
                current=self._plugin_version,

                # update method: pip
                pip="https://github.com/Freeman77/OctoPrint-PrintQueue/archive/{target_version}.zip"
            )
        )


__plugin_name__ = "Print Queue"


def __plugin_load__():
    global __plugin_implementation__
    __plugin_implementation__ = PrintQueuePlugin()

    global __plugin_hooks__
    __plugin_hooks__ = {
        "octoprint.plugin.softwareupdate.check_config": __plugin_implementation__.get_update_information
    }
