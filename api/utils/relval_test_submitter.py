"""
Module for submitting relvals for local testing, eventually to fetch job report
"""
import os
import time
from core_lib.utils.locker import Locker
from core_lib.utils.ssh_executor import SSHExecutor
from core_lib.utils.submitter import Submitter as BaseSubmitter
from core_lib.utils.global_config import Config
from database.database import Database

class RelvalTestSubmitter(BaseSubmitter):
  def add(self, relval, relval_controller):
    """Add relval to the submission queue"""
    prepid = relval.get_prepid()
    super().add_task(prepid, 
      self.submit_relval_test,
      relval = relval,
      controller=relval_controller
    )
  
  def parseParamsFromTest(self, relval):
    """Fetch and return parameters of insterest obtained from local test"""
    db = Database('relval-tests')
    data = db.get(relval.get_prepid())
    stdout = data['test_stdout']
    stdlines = stdout.split('\n')
    params = {}
    steps = ['Step2 ', 'Step3 ']
    for key in steps: params[key.strip()] = {}

    for line in stdlines:
      if line.startswith(steps[0]) or line.startswith(steps[1]):
        step = line.split(' ')[0].strip()
        key = step.strip()
        name = line.strip(step).split(':')[0].split(' ')
        name = '_'.join([a.lower() for a in name if a])
        value = line.split(':')[1].split('(')[0].strip()
        params[key][name] = value
      elif line.startswith('dqm_link: '):
        params['dqm_link'] = line.strip('dqm_link: ').strip()
    return params

  def store_submission_output(self, relval, stdout, exit_code):
    """Store output and exit code of relval test to the database."""
    test_db = Database('relval-tests')
    dbdoc = test_db.get(relval.get_prepid())
    test_stdout = stdout if not dbdoc else dbdoc.get('test_stdout', '') + stdout

    # Check if the test is complete with an exit code
    if exit_code is not None and type(exit_code) == int:
        status = 'done' if exit_code == 0 else 'new'  # 'new' status if test failed
        test_exit_code = str(exit_code)
    else:
        status = 'running'
        test_exit_code = '0'  # Default exit code representing test in progress

    # Update the database document with the new information
    doc = {
        "_id": relval.get_prepid(),
        "test_exit_code": test_exit_code,
        "test_status": status,
        "test_stdout": test_stdout
    }
    test_db.save(doc)

  def submit_relval_test(self, relval, controller):
    """Submit relval for local test"""
    prepid = relval.get_prepid()
    credentials_file = Config.get('credentials_file')
    workspace_dir = Config.get('remote_path').rstrip('/')
    with Locker().get_lock(prepid):
      start_time = time.time()
      relval_db = Database('relvals')
      def execute_scripts():
        ssh = SSHExecutor('lxplus.cern.ch', credentials_file)
        self.prepare_workspace(relval, controller, ssh, workspace_dir)
        exit_code = self.perform_local_tests(ssh, relval, workspace_dir)
        ssh.close_connections()
        return exit_code
      exit_code = execute_scripts()
      # Repeat failures with following exit codes
      minor_codes = [1, 255]
      while exit_code in minor_codes: exit_code = execute_scripts()
      if exit_code:
        for step in relval.get('steps'):
          step.set('resolved_globaltag', '')
        relval.set('status', 'new')
        relval.add_history('approval', 'failed', 'automatic')
      else:
        try:
          # Setting optimal params in relval
          params = self.parseParamsFromTest(relval)
          for step in relval.get('steps'):
            idx = step.get_index_in_parent()
            param = params.get(f'Step{idx+1}', {})
            for p in param:
              value = float(param[p])
              step.set(p, value)
        except Exception as e:
          print(e)
        relval.set('status', 'approved')
        relval.add_history('approval', 'succeeded', 'automatic')
        print('SUCCESS: ', time.time()-start_time, ' sec')
      relval_db.save(relval.get_json())
    return relval

  def prepare_workspace(self, relval, controller, ssh_executor, workspace_dir):
    """
    Clean or create a remote directory and upload all needed files for the test
    """
    prepid = relval.get_prepid()
    self.logger.info('Preparing workspace for %s', prepid)
    # Dump config generation to file
    with open(f'/tmp/{prepid}_test_generate.sh', 'w') as temp_file:
      config_file_content = controller.get_cmsdriver_test(relval)
      temp_file.write(config_file_content)

    # Re-create the directory and create a voms proxy there
    command = [f'rm -rf {workspace_dir}/{prepid}',
                f'mkdir -p {workspace_dir}/{prepid}',
                f'cd {workspace_dir}/{prepid}',
                'voms-proxy-init --rfc -voms cms --valid 1:00 --vomslife 1:00 --verify --out $(pwd)/proxy.txt']
    ssh_executor.execute_command(command)

    # Upload config generation script - cmsDrivers
    ssh_executor.upload_file(f'/tmp/{prepid}_test_generate.sh',
                              f'{workspace_dir}/{prepid}/config_test_generate.sh')

    os.remove(f'/tmp/{prepid}_test_generate.sh')

  def perform_local_tests(self, ssh, relval, workspace_dir):
    """
    Test cmsDriver config files and produce job report
    """
    prepid = relval.get_prepid()
    command = [f'cd {workspace_dir}',
                'export WORKSPACE_DIR=$(pwd)',
                f'cd {prepid}',
                'export RELVAL_DIR=$(pwd)',
                'chmod +x config_test_generate.sh',
                'export X509_USER_PROXY=$(pwd)/proxy.txt',
                'echo "$X509_USER_PROXY"',
                './config_test_generate.sh',
                f'rm -rf {workspace_dir}/{prepid}']
    start_time = time.time()
    stdout = ssh.execute_command_new(command)
    chunk = ''; x = True; iTime=start_time
    runOnce = True
    while x:
      line = stdout.readline()
      chunk += line
      if runOnce:
        self.store_submission_output(relval, str(chunk), None)
        runOnce = False; chunk = ''
      if (time.time() - iTime) > 15:
        iTime = time.time()
        self.store_submission_output(relval, str(chunk), None)
        chunk = ''
      if not line:
        self.store_submission_output(relval, str(chunk), None)
        x = False
    exit_code = stdout.channel.recv_exit_status()
    self.store_submission_output(relval, None, exit_code)

    return exit_code
