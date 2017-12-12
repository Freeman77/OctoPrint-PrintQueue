$(function () {

    var QueueItem = function (data) {
            this.filename = ko.observable(data.filename);
            this.notes = ko.observable(data.notes);
            this.printed_copies = ko.observable(data.printed_copies);
            this.priority = ko.observable(data.priority);
            this.q_id = ko.observable(data.q_id);
            this.status = ko.observable(data.status);
            this.total_copies = ko.observable(data.total_copies).extend({numeric: 0});
    };

    function PrintQueueViewModel(parameters) {
        var self = this;


        //Dependencies
        self.settings = parameters[0];
        self.filesViewModel = parameters[1];
        self.loginState = parameters[2];
        self.printerState = parameters[3];


        // Data
        self.queueItems = ko.observableArray([]);
        self.queueStatus = ko.observable(null);
        self.queueItemForEdit = ko.observable(null);


        var loadingFile = false;
        self.newQItemFilename = ko.observable(null);
        self.newQItemCopies = ko.observable(1).extend({numeric: 0});
        self.newQItemNotes = ko.observable(null);
        self.editQItemCopies = ko.observable(1).extend({numeric: 0});
        self.editQItemNotes = ko.observable(null);


        //Operations
        self.getQueueItems = function() {
            $.ajax({
                url: "plugin/printqueue/queue",
                type: "GET",
                dataType: "json",
                contentType : "application/json",
                success: function(data) {
                    //set queue status
                    self.queueStatus(data.q_status);

                    //if response has items
                    if(data.queue_items.length > 0){
                        //array of valid ids for later removal
                        var valid_ids = [];
                        //loop through items in response
                        $.each(data.queue_items, function (index, db_item) {
                            //look for db_item in local_queue and replace
                            var found = ko.utils.arrayFirst(self.queueItems(), function (queue_item) {
                                return queue_item.q_id() === db_item.q_id;
                            });
                            //if db_item.q_id was found in local array then update changed values
                            if (found) {
                                self.updateQueueItem(found, db_item);
                            } else {
                                //push new
                                self.queueItems.push(new QueueItem(db_item));
                            }
                            //update valid_ids
                            valid_ids.push(db_item.q_id);
                        });
                        //console.log('valid_ids', valid_ids);
                        //console.log('data.queue_items', data.queue_items);
                        //console.log('self.queueItems()', self.queueItems());

                        //remove invalid entries from local queue
                        self.queueItems.remove(function (item) {
                            return !(valid_ids.indexOf(item.q_id()) > -1);
                        });
                    } else {
                        //db is empty, clear local array
                        self.queueItems([]);
                    }
                    //Sort by priority
                    self.queueItems.sort(function (left, right) {
                        return left.priority() == right.priority() ? 0 : (left.priority() < right.priority() ? -1 : 1)}
                    );
                    self.queueItems.valueHasMutated();
                }
            });
        };

        self.updateQueueItem = function (found, updated) {
            if(found.filename() !== updated.filename)
                found.filename(updated.filename);
            if(found.notes() !== updated.notes)
                found.notes(updated.notes);
            if(found.printed_copies() !== updated.printed_copies)
                found.printed_copies(updated.printed_copies);
            if(found.priority() !== updated.priority)
                found.priority(updated.priority);
            if(found.status() !== updated.status)
                found.status(updated.status);
            if(found.total_copies() !== updated.total_copies)
                found.total_copies(updated.total_copies);
        };

        self.addQueueItem = function() {

            var payload = {
                "filename": self.newQItemFilename(),
                "total_copies": self.newQItemCopies(),
                "notes": self.newQItemNotes()
            };

            $.ajax({
                url: "plugin/printqueue/queue/items",
                type: "POST",
                dataType: "json",
                contentType : "application/json",
                data: JSON.stringify(payload),
                success: function(data) {
                    if(data.status == "ok"){
                        self.getQueueItems();
                        self.newQItemFilename(null),
                        self.newQItemCopies(null),
                        self.newQItemNotes(null)
                        $("#queue-item-modal-new").modal("hide");
                    }
                }
            });
        };

        self.removeQueueItem = function (data) {
            //var idx = self.queueItems.indexOf(data);
            //self.queueItems.splice(idx, 1);
            var item = data;
            $.ajax({
                url: "plugin/printqueue/queue/items/" + data.q_id(),
                type: "DELETE",
                dataType: "json",
                success: function (data) {
                    if(data.status == "ok"){
                        self.queueItems.remove(item);
                        self.getQueueItems();
                    }
                }
            });

        };

        self.sendQueueCommand = function (data, event) {
            var payload = {
                "command": event.target.value
            };

            $.ajax({
                url: "plugin/printqueue/queue",
                type: "POST",
                dataType: "json",
                contentType : "application/json",
                data: JSON.stringify(payload),
                success: function(data) {
                    console.log('success', data)
                    self.getQueueItems();
                }
            });
        }

        self.swap = function (to, from) {
            objTo = self.queueItems()[to];
            objFrom = self.queueItems()[from];
            self.queueItems()[to] = objFrom;
            self.queueItems()[from] = objTo;
            self.queueItems.valueHasMutated();
            self.getQueueItems();
        }

        self.changePriority = function (move, data) {
            var item = data
            var payload = {
                "q_id": data.q_id(),
                "move": move
            };
            //console.log('changePriority', data);
            //console.log('priorityPayload', payload);
            $.ajax({
                url: "plugin/printqueue/queue/items/priority",
                type: "POST",
                dataType: "json",
                contentType : "application/json",
                data: JSON.stringify(payload),
                success: function(data) {
                    if(data.status == "ok"){
                        if(move=="up"){
                            var idx = self.queueItems.indexOf(item)
                            self.swap(idx, idx-1);
                        }
                        if(move=="down"){
                            var idx = self.queueItems.indexOf(item)
                            self.swap(idx, idx+1);
                        }
                    }
                }
            });
        }

        self.clearAllQItems = function () {
            self.getQueueItems();
            self.queueItems().forEach(function (item) {
                self.removeQueueItem(item);
            })
        }

        self.onStartupComplete = function() {
            // Add new queue items buttons
            addQueueItemButtons();
            //Load queue items
            self.getQueueItems();
        }

        self.changeNewQItem_Copies = function (operation) {
            console.log('operation', operation);
            if(operation=="minus"){
                self.newQItemCopies(self.newQItemCopies() - 1);
            }
            if(operation=="plus"){
                self.newQItemCopies(self.newQItemCopies() + 1);
            }
        };

        self.changeEditQItem_Copies = function (operation) {
            console.log('operation', operation);
            if(operation=="minus"){
                self.editQItemCopies(self.editQItemCopies() - 1);
            }
            if(operation=="plus"){
                self.editQItemCopies(self.editQItemCopies() + 1);
            }
        };

        self.updateQueueItemDetails = function () {
            console.log('q_item_edit', self.queueItemForEdit());
            var payload = {
                "q_id": self.queueItemForEdit().q_id(),
                "total_copies": self.editQItemCopies(),
                "notes": self.editQItemNotes()
            };

            $.ajax({
                url: "plugin/printqueue/queue/items",
                type: "PUT",
                dataType: "json",
                contentType : "application/json",
                data: JSON.stringify(payload),
                success: function(data) {
                    if(data.status == "ok"){
                        self.getQueueItems();
                        $("#queue-item-modal-edit").modal("hide");
                    }
                }
            });
        };

        //Copied from GCode Editor plugin
        self.onAllBound = function(payload) {
            // Modified from M33-Fio https://github.com/donovan6000/M33-Fio/blob/master/octoprint_m33fio/static/js/m33fio.js#L18516
            // Go through all view models
            for(var viewModel in payload) {

                // Otherwise check if view model is files view model
                if(payload[viewModel].constructor.name === "GcodeFilesViewModel" || payload[viewModel].constructor.name === "FilesViewModel") {

                    // Set files
                    self.files = payload[viewModel];

                    // Replace list helper update items
                    var originalUpdateItems = self.files.listHelper._updateItems;
                    self.files.listHelper._updateItems = function() {

                        // Update items
                        originalUpdateItems();

                        // Add edit buttons to G-code
                        addQueueItemButtons();
                    }
                }
            }
        }

        self.showEditQueueItem = function(data){
            self.queueItemForEdit(data);
            self.editQItemCopies(data.total_copies());
            self.editQItemNotes(data.notes());
            $('#queue-item-modal-edit').modal('show');
        };

        function addQueueItemButtons() {
            // Remove all edit buttons
            $("#files div.gcode_files div.entry .action-buttons div.btn-mini.addQItem").remove();
            // Go through all file entries
            $("#files div.gcode_files div.entry .action-buttons").each(function() {
                // Check if file is G-code
                if($(this).children().children("i.icon-print, i.fa.fa-print").length)
                    // Add edit button
                    $(this).append("\
                        <div class=\"btn btn-mini addQItem\" title=\"Add to Queue\">\
                            <i class=\"icon-plus\"></i>\
                        </div>\
                    ");
            });

            // Check if user isn't logged in
            if(!self.loginState.loggedIn()) {
                // Disable edit buttons
                $("#files div.gcode_files div.entry .action-buttons div.btn-mini.addQItem").addClass("disabled");
            }
            // Edit button click event
            $("#files div.gcode_files div.entry .action-buttons div.btn-mini.addQItem").click(function() {
                // Initialize variables
                var button = $(this);
                // Blur self
                button.blur();
                // Check if button is not disabled
                if(!button.hasClass("disabled")) {
                    // Check if not already loading file
                    if(!loadingFile) {
                        // Set loading file
                        loadingFile = true;
                        // Enable other edit buttons
                        $("#files div.gcode_files div.entry .action-buttons div.btn-mini.addQItem").removeClass("disabled");
                        // Set icon to spinning animation
                        button.addClass("disabled").children("i").removeClass("icon-plus").addClass("icon-spinner icon-spin");

                        setTimeout(function() {
                            // Show Add queue item dialog
                            showAddQueueItem(
                                button.parent().children("a.btn-mini").attr("href"),                    // url,
                                button.parent().parent().children("div").eq(0).text(),                  // name,
                                function() {                                                            // onloadCallback
                                    // Clear loading file
                                    loadingFile = false;
                                    // Restore icon and enable button
                                    button.removeClass("disabled").children("i").removeClass("icon-spinner icon-spin").addClass("icon-plus");
                                }
                            );
                        }, 200);
                    }
                }
            });
        }

        function showAddQueueItem(url, name, onloadCallback) {
            // Send request
            $.ajax({
                url: url,
                type: "GET",
                dataType: "text",
                data: null,
                contentType: "application/x-www-form-urlencoded; charset=UTF-8",
                traditional: true,
                processData: true,
                headers: {
                    "Pragma": "no-cache",
                    "Expires": "0",
                    "Cache-Control": "no-cache, no-store, must-revalidate"
            }

            // Done
            }).done(function(data) {
                onloadCallback();
                self.newQItemFilename(name);
                self.newQItemCopies(1);
                self.newQItemNotes("");
                $("#queue-item-modal-new").modal("show");
            });
        }

        // https://github.com/foosel/OctoPrint/blob/master/src/octoprint/static/js/app/viewmodels/slicing.js#L294
        self._sanitize = function(name) {
            return name.replace(/[^a-zA-Z0-9\-_\.\(\) ]/g, "").replace(/ /g, "_");
        };

        // Animation callbacks for the queue list
        self.showQueueElement = function(elem) { if (elem.nodeType === 1) $(elem).hide().fadeIn("fast") };
        self.hideQueueElement = function(elem) { if (elem.nodeType === 1) $(elem).fadeOut("fast", function() {$(elem).remove(); }) }

    }

    // Here's a custom Knockout binding that makes elements shown/hidden via jQuery's fadeIn()/fadeOut() methods
    // Could be stored in a separate utility library
    ko.bindingHandlers.fadeVisible = {
        init: function(element, valueAccessor) {
            // Initially set the element to be instantly visible/hidden depending on the value
            var value = valueAccessor();
            $(element).toggle(ko.unwrap(value)); // Use "unwrapObservable" so we can handle values that may or may not be observable
        },
        update: function(element, valueAccessor) {
            // Whenever the value subsequently changes, slowly fade the element in or out
            var value = valueAccessor();
            ko.unwrap(value) ? $(element).fadeIn() : $(element).fadeOut();
        }
    };

    // Forcing input to be numeric
    // http://knockoutjs.com/documentation/extenders.html
    ko.extenders.numeric = function(target, precision) {
        //create a writable computed observable to intercept writes to our observable
        var result = ko.pureComputed({
            read: target,  //always return the original observables value
            write: function(newValue) {
                var current = target(),
                    roundingMultiplier = Math.pow(10, precision),
                    newValueAsNum = isNaN(newValue) ? 0 : +newValue,
                    valueToWrite = Math.round(newValueAsNum * roundingMultiplier) / roundingMultiplier;
                //only write if it changed
                if (valueToWrite !== current) {
                    target(valueToWrite);
                } else {
                    //if the rounded value is the same, but a different value was written, force a notification for the current field
                    if (newValue !== current) {
                        target.notifySubscribers(valueToWrite);
                    }
                }
            }
        }).extend({ notify: 'always' });
        //initialize with current value to make sure it is rounded appropriately
        result(target());
        //return the new computed observable
        return result;
    };

    // This is how our plugin registers itself with the application, by adding some configuration
    // information to the global variable OCTOPRINT_VIEWMODELS
    OCTOPRINT_VIEWMODELS.push([
        // This is the constructor to call for instantiating the plugin
        PrintQueueViewModel,

        // This is a list of dependencies to inject into the plugin, the order which you request
        // here is the order in which the dependencies will be injected into your view model upon
        // instantiation via the parameters argument
        ["settingsViewModel", "filesViewModel", "loginStateViewModel", "printerStateViewModel"],

        // Finally, this is the list of selectors for all elements we want this view model to be bound to.
        ["#tab_plugin_printqueue"]

    ]);

});
