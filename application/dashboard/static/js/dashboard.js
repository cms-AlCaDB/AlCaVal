function fetchWorkerInfo(){
  fetch('api/system/workers').then(res => res.json()).then(d =>{
    submissionWorkers = d.response;
    $('#threads').html('Submission threads ('+Object.keys(submissionWorkers).length+')')
    $('#threads-list').html("")
    for (var i in submissionWorkers) {
      let job_name = submissionWorkers[i].job_name;
      let job_time = submissionWorkers[i].job_time;
      var info = job_name ? 'working on ' + job_name + ' for ' + job_time + 's' : 'not busy'
      $('#threads-list').append('<li>Thread '+i+' is '+info+'</li>')
    }
  })
}

function fetchQueueInfo() {
  fetch('api/system/queue').then(res => res.json()).then(d =>{
    submissionQueue = d.response;
    $('#queue').html('Submission queue ('+submissionQueue.length+')')
    $('#queue-list').html("")
    for (var i = 0; i < submissionQueue.length; i++) {
      $('#queue-list').append('<li><a href="relvals?prepid="'+submissionQueue[i]+' title="Show this RelVal"></a> is waiting in queue</li>')
    }
  })
}

function fetchLocksInfo() {
  fetch('api/system/locks').then(res => res.json()).then(d =>{
    locks = d.response;
    $('#locks').html('Locked objects  ('+Object.keys(locks).length+')')
    $('#locks-list').html("")
    for (var i in locks) {
      let style=locks[i] ? "color: red; font-weight: bold;" : "";
      $('#locks-list').append('<li style="'+style+'"> '+locks[i]+': '+i+'</li>')
    }
  })
}

function fetchSettings() {
  fetch('api/settings/get').then(res => res.json()).then(d =>{
    settings = d.response;
  })
}

function fetchUptime() {
  fetch('api/system/uptime').then(res => res.json()).then(d =>{
    uptime = d.response;
    let uptime_content = uptime.days+' days '+uptime.hours+' hours '+uptime.minutes+' minutes '+uptime.seconds+' seconds'
    $('#system-uptime-list').html('<li>'+uptime_content+'</li>');
  }) 
}

function fetchBuildInfo() {
  fetch('api/system/build_info').then(res => res.json()).then(d =>{
    buildInfo = d.response;
    $('#build-info-list').html('<li>Build version: '+buildInfo+'</li>')
  })
}