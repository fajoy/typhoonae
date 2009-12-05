function updateMessage() {
    $.getJSON("getnote", {}, function(data) {   
        $("#message").text(data['message']);
    });   
    setTimeout('updateMessage()', 3000);
};

$(document).ready(function() {
   updateMessage();
})
