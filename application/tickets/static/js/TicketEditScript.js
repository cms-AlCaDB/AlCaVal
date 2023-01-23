function showModal(e){
  e.preventDefault();
  $('#event-content-modal').modal({show: true})
}

function showRunsModal(e){
  e.preventDefault();
  $('#suggested-runs-modal').modal({show: true})
}

function addnEventCalculator(){
  suggestRuns = '<button class="btn btn-sm btn-outline-info" onclick="showRunsModal(event);">Suggested Runs</button>';
  nEventButton = '<button class="btn btn-sm btn-outline-info" onclick="showModal(event);">Get Events</button>';
  document.getElementById("input_runs").insertAdjacentHTML('afterend', `<div style="display:grid">${nEventButton}${suggestRuns}</div>`);
}

function addHelpIcons(){
  grayHelper = '<tr class="small-footers"><td></td><td><small style="color: gray"><i class="bi bi-arrow-up-circle"></i>'
  var nstreams_help = `${grayHelper} If number of streams is 0, default value will be used</small></td></tr>`
  document.getElementById("n_streams").parentNode.parentNode.insertAdjacentHTML('afterend', nstreams_help)

  var common_gt_help = "Common Prompt GT is usually same as target prompt GT. This field is required if you are using HLT GTs. It will be used in RECO stage of the HLT workflow"
  common_gt_help = '<span id="commong-gt-help-icon" class="help-icons" data-toggle="popover" data-content="'+common_gt_help+'"><i class="bi bi-question-circle-fill"></i></span>'
  document.getElementById("common_prompt_gt").insertAdjacentHTML('afterend', common_gt_help)

  var CMSSW_release_help = "You need to use latest version of CMSSW"
  CMSSW_release_help = '<span id="CMSSW_release_help-icon" class="help-icons" data-toggle="popover" data-content="'+CMSSW_release_help+'"><i class="bi bi-question-circle-fill"></i></span>'
  document.getElementById("CMSSW_release_help").insertAdjacentHTML('afterend', CMSSW_release_help)

  var widHelp = `${grayHelper} This is handled by FTV managers, please ignore if you are not the one</small></td></tr>`
  document.getElementById("workflow_ids").parentNode.parentNode.insertAdjacentHTML('afterend', widHelp)
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
  fetch(`https://api.github.com/repos/cms-sw/cmssw/releases/tags/${value}`).then(res => {
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
  addnEventCalculator()
  track_matrix_select()	

  $('#matrix').on( "change", function( event ) {
    track_matrix_select()
    $('#matrix-help-icon').css({'animation-name': 'blink', 'animation-duration': '0.5s', 'animation-iteration-count': '3'})
  })

  $('#cmssw_release').on( "change", function( event ) {
    validate_cmssw(this.id)
  })

  $('#event-content-modal').on('show.bs.modal', (event)=>{
    var modal = $(this)
    $("#event-modal-content").html('Loading...')
    fetch('/tickets/fetch-events', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({
                  datasets: $('#input_datasets').val(), 
                  runs: $('#input_runs').val(),
                  })
    }).
    then(res => res.json()).
    then(data => {
      modal.find('#event-modal-content').html(data.response)
    })
  })


  $('#suggested-runs-modal').on('show.bs.modal', (event)=>{
    var modal = $(this)
    $("#suggested-runs").html('Loading...')
    fetch('/api/search?db_name=relvals&status=submitted&limit=100').
    then(res => res.json()).
    then(data => {
      data = data.response.results
      output = {}
      data.forEach(relval => {
        dataset = relval.steps[0].input.dataset
        run1 = relval.steps[0].input.lumisection
        run2 = relval.steps[0].input.run
        run = Object.keys(run1).concat(run2)
        output[dataset] = output[dataset]? output[dataset].concat(run): run
      });
      datasetList = Object.keys(output); datasetList.sort();
      text = '<table class="table" width=100%>'
      text += '<thead><tr><th>Dataset</th><th>Runs</th></tr></thead>'
      text += '<tbody>'
      datasetList.forEach(key => {text += `<tr><td>${key}</td><td>${[...new Set(output[key])].join(', ')}</td></tr>`})
      text += '</tdoby></table>'
      console.log(text)
      modal.find('#suggested-runs').html(text)
    })
  })

  // Validate InputRuns
  validate_input_runs()
});

