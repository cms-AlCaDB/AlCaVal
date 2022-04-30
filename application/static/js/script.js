$(document).ready(function() {
    $(function(){
        // $('.navbar-nav li a').click(function(){ $(this).parent().addClass('active').siblings().removeClass('active') });
        $('.navbar-nav li a').filter(function(){ return this.href==location.href}).parent().addClass('active').siblings().removeClass('active')
    });
});

function activateConfirmModal(title, body){
    $('.modal-title').html(title);
    $('.modal-body').html(body);
    $('#confirmationModal').modal({keyboard: true});
    return true;
}

function alertModal(title, message){
    $('.modal-title').html(title);
    $('.modal-body').html(message);
    $('#alertModal').modal({keyboard: true});
}