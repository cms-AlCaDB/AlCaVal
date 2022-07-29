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

// Fade out success flash message
$(document).ready(function() {
    $('.alert-success').fadeOut(3000);
    $('#goto_workflow_classifier_modal').on('click', function() {
        $('#confirmationModal').modal('toggle');
        $('#exampleModal').modal('toggle');
    });
});

//------------------------------------------------------------------------------
// Change border color on select for the form inputs
function toggle_border_color(obj) {
    if (obj.value != '') {
        obj.style = "border-color: black"
    } else {
        obj.style = ""
    }
}
$( document ).ready(function() {
    $("select:not(select[name$=list_length]), textarea, input:not('#submit')").each(function() {
        toggle_border_color(this)
    })
    $("select:not(select[name$=list_length]), textarea, input:not('#submit')").on("change", function() {
        toggle_border_color(this)
    })
})
//------------------------------------------------------------------------------
// Function for validating run number and lumisectin field in ticket and relval form
function prettyPrint(id) {
    var ugly = document.getElementById(id).value;
    var obj = JSON.parse(ugly);
    // var pretty = JSON.stringify(obj, undefined, 4);
    pretty = '{\n'
    Object.keys(obj).forEach(function(key){
        pretty += '\t"'+key+'": '+JSON.stringify(obj[key])
        if (Object.keys(obj)[Object.keys(obj).length - 1] != key)
            pretty += ',\n'
    })
    pretty += '\n}'
    document.getElementById(id).value = pretty;
}

function add_number_of_runs(id, runs){
    element = $('label[for="'+id+'"]')
    label = element.text().split(" (")[0]
    if(runs.length == 1 && runs[0]=='') {
        element.html(label+' (0)')
        return
    } else {
        element.html(label+' ('+runs.length+')')
    }
}

function validateRunNumbers(id) {
    var lumiid = document.getElementById('nrun_error_id')
    if (lumiid) lumiid.parentNode.parentNode.remove()
    try{
      var runs = document.getElementById(id).value.split(',').filter(function function_name(run) {
          return run.trim().length >=1
      })
      add_number_of_runs(id, runs)
      if (!runs.length) return ;
      runs = document.getElementById(id).value.split(',')
      for (let run in runs){
        if (runs[run].trim() == '')
          throw new Error("Can not have empty spaces, remove extra comma!")
        if (runs[run].includes('\n'))
          throw new Error("New line seperation is not allowed")
        if (!Number(runs[run]))
          throw new Error(runs[run] + " is not valid run")
        if (runs[run].includes('.'))
          throw new Error(runs[run] + " is not valid run")
        if (Number(runs[run]) < 200000 || Number(runs[run]) > 400000)
          throw new Error(runs[run] + " is not valid run")
      }
      var el = '<td></td><td style="padding-top: unset;"><small id="nrun_error_id" style="color: green">Acceptable format</small></td>'
      document.getElementById(id).parentNode.parentNode.insertAdjacentHTML('afterend', el)
    }catch (e){
      var el = '<td></td><td style="padding-top: unset;"><small id="nrun_error_id" style="color: red">'+e+'</small></td>'
      document.getElementById(id).parentNode.parentNode.insertAdjacentHTML('afterend', el)
    }
}
//------------------------------------------------------------------------------