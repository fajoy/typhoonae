var last_key = null;

function updateMessage() {
    $.getJSON("getnote", {'last_key': last_key}, function(data) {   
        $("#message").text(data['message']);
        last_key = data['key'];
    });   
    setTimeout('updateMessage()', 3000);
};

$(document).ready(function() {
   $("#message").text('waiting...');
   updateMessage();
})
