function create_jira_ticket(prepid) {
  $('body').addClass('loading');
  fetch('/api/tickets/get/'+prepid).then(res => res.json()).then(ticket => {
    fetch('/api/tickets/jira_info/'+prepid).then(res => res.json()).then(jira_json => {
      open_jira_modal(prepid, ticket.response, jira_json)
      $('body').removeClass('loading');
    })
  })
}

function open_jira_modal(prepid, ticket, jira_json) {
  $('#jiraModal').on('show.bs.modal', function (event) {
    var modal = $(this)
    modal.find('#jiraModalLabel').html('<img src="https://its.cern.ch/jira/s/2ji1vl/822002/1fdycnt/_/jira-logo-scaled.png" alt="Jira" height="30"/> Creating new ticket')
    modal.find('#jira_prepid_id').val(ticket.prepid)
    modal.find('#jira_summary_id').val(jira_json.response.jira_info.summary)
    modal.find('#jira_description_id').val(jira_json.response.jira_info.description)
    modal.find('#jira_comp_id').val(jira_json.response.jira_info.components)
    modal.find('#jira_label_id').val(jira_json.response.jira_info.labels)
    $(this).off('show.bs.modal')
  })
  $('#jiraModal').modal({backdrop: 'static', keyboard: false})
}

$(document).ready(function(){
  $( "#jira_submit_id" ).on( "click", function( e ) {
    e.preventDefault()
    $('#jiraModal').modal('toggle');     
    var data = {}
    $('#create-jira-form').serializeArray().forEach(function(e){
      data[e.name] =  e.value
    })
    jira_api(data)
  })
})

function getresponse(res){
  if (res.status >= 200 && res.status <= 299) {
    return res.json();
  } else {
    throw Error(res.statusText);
  }
}

function jira_api(data) {
  $('body').addClass('loading');    
  fetch('api/jira/create',
    {
      method: 'POST',
      body: JSON.stringify(data),
      headers: {'Content-Type': 'application/json'}
    }
  ).then(res => getresponse(res)).then(dat => {
    if (dat.success){
      fetch('/api/tickets/get/'+dat.response.prepid).then(res => res.json()).then(data => {
        data.response.jira_ticket = dat.response.jira_ticket
        update_jira_in_ticket(data.response)
      })
    } else {
      throw Error(dat.message)
    }
  }).catch(error => {
    $('body').removeClass('loading');
    alertModal('There was a problem with the request: api/jira/create', error);
  })
}

function update_jira_in_ticket(ticket_json) {
  fetch('/api/tickets/update',
    {
      method: 'POST',
      body: JSON.stringify(ticket_json),
      headers: {'Content-Type': 'application/x-www-form-urlencoded'}
    }
  ).then(res => getresponse(res)).then(data => {
    update_jira_in_relvals(ticket_json.created_relvals, ticket_json.jira_ticket)
  }).catch(error =>{
    $('body').removeClass('loading');
    alertModal('There was a problem with the request: /api/tickets/update', error);
  })
}

function update_jira_in_relvals(created_relvals, jira_ticket) {
  if (!created_relvals.length) {
    window.location.reload(false);
    window.onload = function() { $('body').removeClass('loading');}
  }
  created_relvals.forEach(function(relval_prepid){
    fetch('/api/relvals/get/'+relval_prepid).then(res => res.json()).then(data => {
      data.response.jira_ticket = jira_ticket
      update_jira_in_relval(data.response, created_relvals[created_relvals.length-1])
    })
  })
}

function update_jira_in_relval(relval_json, lastEl) {
  fetch('api/relvals/update',
    {
      method: 'POST',
      body: JSON.stringify(relval_json),
      headers: {'Content-Type': 'application/json'}
    }
  ).then(res => getresponse(res)).then(data => {
    console.log('relval '+ relval_json.prepid +' is updated with jira ticket.')
    if (relval_json.prepid == lastEl) {
      window.location.reload(false);
      window.onload = function() { $('body').removeClass('loading');}
    }
  }).catch(error =>{
    $('body').removeClass('loading');
    alertModal('There was a problem with the request: /api/relvals/update', error);
  })
}
