$(document).ready(function() {
    $(function(){
        // $('.navbar-nav li a').click(function(){ $(this).parent().addClass('active').siblings().removeClass('active') });
        $('.navbar-nav li a').filter(function(){ return this.href==location.href}).parent().addClass('active').siblings().removeClass('active')
    });
});
