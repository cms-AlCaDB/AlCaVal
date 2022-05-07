$(document).ready(function() {
    $(function(){
        // $('.navbar-nav li a').click(function(){ $(this).parent().addClass('active').siblings().removeClass('active') });
        $('.navbar-nav li a').filter(function(){ return this.href==location.href}).parent().addClass('active').siblings().removeClass('active')
    });
});

function activateConfirmModal(title, body){
    $('#confirmationModalLongTitle').html(title);
    $('#confirmationModalBody').html(body);
    $('#confirmationModal').modal({keyboard: true});
    return true;
}

function alertModal(title, message){
    $('#alertModalLongTitle').html(title);
    $('#alertModalBody').html(message);
    $('#alertModal').modal({keyboard: true});
}

function formToJSON(array) {
    var d = {};
    $(array).each(function() {
        if (d[this.name] !== undefined){
            if (!Array.isArray(d[this.name])) {
                d[this.name] = [d[this.name]];
            }
            d[this.name].push(parseFloat(this.value));
        }else{
            d[this.name] = [parseFloat(this.value)];
        }
    });
    return d;
}