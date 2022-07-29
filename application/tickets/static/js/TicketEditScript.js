
function addHelpIcons(){
	var nstreams_help = '<tr class="small-footers"><td></td><td><small style="color: gray"><i class="bi bi-arrow-up-circle"></i> If number of streams is 0, default value will be used</small></td></tr>'
	document.getElementById("n_streams").parentNode.parentNode.insertAdjacentHTML('afterend', nstreams_help)

	var common_gt_help = "Common Prompt GT is usually same as target prompt GT. This field is required if you are using HLT GTs. It will be used in RECO stage of the HLT workflow"
	common_gt_help = '<span id="commong-gt-help-icon" class="help-icons" data-toggle="popover" data-content="'+common_gt_help+'"><i class="bi bi-question-circle-fill"></i></span>'
	document.getElementById("common_prompt_gt").insertAdjacentHTML('afterend', common_gt_help)
}

function track_matrix_select() {
    var value = $('#matrix').val()
    var wid_help = "Checkout list of Workflow IDs <a href='https://github.com/cms-sw/cmssw/tree/master/Configuration/PyReleaseValidation/python/relval_"+value+".py' target='_blank' rel='noopener noreferrer'>here</a>."
    var wid_help_alca = "Checkout list of Workflow IDs <a href='https://github.com/cms-AlCaDB/AlCaWorkflows/blob/main/relval_alca.py' target='_blank' rel='noopener noreferrer'>here</a>"

    if (value == 'alca'){
        wid_help = '<span id="matrix-help-icon" class="help-icons" data-toggle="popover" data-content="'+wid_help_alca+'"><i class="bi bi-question-circle-fill"></i></span>'
    } else {
        wid_help = '<span id="matrix-help-icon" class="help-icons" data-toggle="popover" data-content="'+wid_help+'"><i class="bi bi-question-circle-fill"></i></span>'
    }
    if ($('#matrix-help-icon').length){
        document.getElementById("matrix-help-icon").remove()
    }
    document.getElementById("workflow_ids").insertAdjacentHTML('afterend', wid_help)
    $('[data-toggle="popover"]').popover({
        html:true,
    })
}

function validate_cmssw(id) {
    var release = document.getElementById('cmssw_release_error_id')
    if (release) release.parentNode.parentNode.remove()
    value = document.getElementById(id).value
    fetch('https://api.github.com/repos/cms-sw/cmssw/releases/tags/'+value).then(res => {
        if (res.status == 200) {
            var el = '<td></td><td style="padding-top: unset;"><small id="cmssw_release_error_id" style="color: green">Valid CMSSW release</small></td>'
            document.getElementById(id).parentNode.parentNode.insertAdjacentHTML('afterend', el)
        } else {
            var el = '<td></td><td style="padding-top: unset;"><small id="cmssw_release_error_id" style="color: red">CMSSW release is not valid</small></td>'
            document.getElementById(id).parentNode.parentNode.insertAdjacentHTML('afterend', el)
        }
    })
}


function validate_input_runs(){
    validateJSON_or_List('input_runs')
}

function validateJSON_or_List(id) {
    var input_runs_error = document.getElementById('nrun_error_id')
    if (input_runs_error) input_runs_error.parentNode.parentNode.remove()
    value = document.getElementById(id).value
    if (value.includes("{") | value.includes("}")){
        validateJSON(id)
    } else {
        validateRunNumbers(id)
    }
}

function validateJSON(id) {
    var el = ''
    try{
        value = document.getElementById(id).value.replaceAll('\'', '\"')
        var cpos = $('#'+id).prop("selectionStart")
        document.getElementById(id).value = value
        document.getElementById(id).setSelectionRange(cpos, cpos);
        add_number_of_runs(id, [])
        var json = JSON.parse(value);
        add_number_of_runs(id, Object.keys(json))
        prettyPrint(id)
        el = '<td></td><td style="padding-top: unset;"><small id="nrun_error_id" style="color: green">Valid JSON</small></td>'
    }catch (e){
        el = '<td></td><td style="padding-top: unset;"><small id="nrun_error_id" style="color:red">Invalid JSON: '+e+'</small></td>'
    }
    document.getElementById(id).parentNode.parentNode.insertAdjacentHTML('afterend', el)
}

$(document).mouseup(function (e) {
    // Hide popover when clicked anywhere else
    if(!($(e.target).hasClass("popover-content"))){
        $(".popover").popover('hide');
    }
 });

function cancel(){window.location = '/tickets';}

$(document).ready(function(){
	addHelpIcons()
	track_matrix_select()	

	$('#matrix').on( "change", function( event ) {
	    track_matrix_select()
	    $('#matrix-help-icon').css({'animation-name': 'blink', 'animation-duration': '0.5s', 'animation-iteration-count': '3'})
	})

    $('#cmssw_release').on( "change", function( event ) {
        validate_cmssw(this.id)
    })

    // Validate InputRuns
    validate_input_runs()
});

