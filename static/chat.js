// Copyright 2009 FriendFeed
//
// Licensed under the Apache License, Version 2.0 (the "License"); you may
// not use this file except in compliance with the License. You may obtain
// a copy of the License at
//
//     http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
// WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
// License for the specific language governing permissions and limitations
// under the License.

$(document).ready(function() {
    if (!window.console) window.console = {};
    if (!window.console.log) window.console.log = function() {};

    $("#messageform").live("submit", function() {
        newMessage($(this));
        return false;
    });
    $("#messageform").live("keypress", function(e) {
        if (e.keyCode == 13) {
            newMessage($(this));
            return false;
        }
    });
    $("#message").select();


    $('a.play').click(function(e) {
        e.preventDefault();
        var url = $(this).attr('href');
        playSong(url);
        return false;
    });

    // Send a message that user has entered the room.
    // Must do this client side so that it's broadcast
    // to the right chat server
    newMessage($("#messageform"), "\\enter");

    updater.poll();
});

function playSong(url){
    console.log("Playing song " + url);
    var audio = $('<audio>').attr('controls','controls').attr('autoplay','autoplay');
    $('<source>').attr('src', url).attr("type","audio/mpeg").appendTo(audio);
    $('div.song').html(audio);
}

function newMessage(form, body) {
    var message = form.formToDict();
    if(body){
        message["body"] = body;
    }

    var disabled = form.find("input[type=submit]");
    var host = $(".room").attr("data-host");
    var url = host + "/a/message/new";

    disabled.disable();
    $.postJSON(url, message, function(response) {
        updater.processMessage(response);
        if (message.id) {
            form.parent().remove();
        } else {
            form.find("input[type=text]").val("").select();
            disabled.enable();
        }
    });
}

function getCookie(name) {
    var r = document.cookie.match("\\b" + name + "=([^;]*)\\b");
    return r ? r[1] : undefined;
}

jQuery.postJSON = function(url, args, callback) {
    args._xsrf = getCookie("_xsrf");
    $.ajax({url: url, data: $.param(args), dataType: "text", type: "POST",
            crossDomain: true,
            xhrFields: {
                withCredentials: true
            },
            success: function(response) {
        if (callback) callback(eval("(" + response + ")"));
    }, error: function(response) {
        console.log("ERROR:", response)
    }});
};

if (typeof String.prototype.startsWith != 'function') {
    String.prototype.startsWith = function (str){
        return this.indexOf(str) == 0;
    };
}

jQuery.fn.formToDict = function() {
    var fields = this.serializeArray();
    var json = {}
    for (var i = 0; i < fields.length; i++) {
        json[fields[i].name] = fields[i].value;
    }
    if (json.next) delete json.next;
    return json;
};

jQuery.fn.disable = function() {
    this.enable(false);
    return this;
};

jQuery.fn.enable = function(opt_enable) {
    if (arguments.length && !opt_enable) {
        this.attr("disabled", "disabled");
    } else {
        this.removeAttr("disabled");
    }
    return this;
};

var updater = {
    errorSleepTime: 500,
    cursor: null,

    poll: function() {
        var room = $(".room").attr("data-id");
        var host = $(".room").attr("data-host");
        var url = host + "/a/message/updates";

        var args = {"_xsrf": getCookie("_xsrf"), "room" : room};


        console.log("Requesting update for room " + room + " from host " + host + " and url " + url);

        if (updater.cursor) args.cursor = updater.cursor;

        $.ajax({url: url, type: "POST", dataType: "text",
                crossDomain: true,
                xhrFields: {
                    withCredentials: true
                },
                data: $.param(args), success: updater.onSuccess,
                error: updater.onError});
    },

    onSuccess: function(response) {
        try {
            updater.newMessages(eval("(" + response + ")"));
        } catch (e) {
            updater.onError();
            return;
        }
        updater.errorSleepTime = 500;
        window.setTimeout(updater.poll, 0);
    },

    onError: function(response) {
        updater.errorSleepTime *= 2;
        console.log("Poll error; sleeping for", updater.errorSleepTime, "ms");
        window.setTimeout(updater.poll, updater.errorSleepTime);
    },

    newMessages: function(response) {
        if (!response.messages) return;
        updater.cursor = response.cursor;
        var messages = response.messages;
        updater.cursor = messages[messages.length - 1].id;
        console.log(messages.length, "new messages, cursor:", updater.cursor);
        for (var i = 0; i < messages.length; i++) {
            updater.processMessage(messages[i]);
        }
    },

    processMessage: function(message) {
        console.log("Processing message [" + message.body + "]");

        updater.showMessage(message)

        if(message.body.startsWith("\\song")){
            updater.processSongMessage(message)
        }
        else if(message.body.startsWith("\\enter")){
            updater.processEnterMessage(message)
        }

    },

    showMessage: function(message){
        var existing = $("#m" + message.id);
        if (existing.length > 0) return;

        var html = '<div class="message" id=m'+message.id+'><b>'+message.from+':</b> '+message.body+'</div>';

        var node = $(html);
        node.hide();
        $("#inbox").append(node);
        node.slideDown();
    },

    processSongMessage: function(message){
        var song = message.body.substring(6);
        console.log("Message contains request to play song [" + song + "]");
        $('#music h2').html("Now Playing - " + song);
        playSong($('#' + song).attr('href'));
    },

    processEnterMessage: function(message){
        var user = message.from;
        console.log("Message announces entrance of  [" + user + "]");

        var existing = $("#users #user_" + user);
        if (existing.length > 0) return;

        $('#users ul').append('<li id="user_' + user + '">' + user + '</li>')
    }
};
