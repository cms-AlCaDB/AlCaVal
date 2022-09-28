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
  
  def store_submission_output(self, relval, stdout, exit_code):
    """Novice way to store std output to db. 
    if exit_code is other that 'None' then status is set to 'done'
    """
    test_db = Database('relval-tests')
    dbdoc = test_db.get(relval.get_prepid())
    if not dbdoc:
      test_stdout = stdout
      new = True
    else:
      test_stdout = dbdoc['test_stdout']
      new = dbdoc['test_status']=='done' and (exit_code==None)
    stdout = None if type(exit_code)==int else stdout if new else test_stdout + stdout
    status = 'done' if type(exit_code)==int else 'running'
    doc = {"_id": relval.get_prepid(),
           "test_exit_code": str(exit_code) if type(exit_code)==int else '0',
           "test_status": status
          } | {"test_stdout": stdout if stdout else test_stdout}
    test_db.save(doc)
  
  def submit_relval_test(self, relval, controller):
    """Submit relval for local test"""
    prepid = relval.get_prepid()
    credentials_file = Config.get('credentials_file')
    workspace_dir = Config.get('remote_path').rstrip('/')
    with Locker().get_lock(prepid):
      start_time = time.time()
      relval_db = Database('relvals')
      ssh = SSHExecutor('lxplus.cern.ch', credentials_file)
      self.prepare_workspace(relval, controller, ssh, workspace_dir)
      exit_code = self.perform_local_tests(ssh, relval, workspace_dir)
      ssh.close_connections()
      relval.set('status', 'approved')
      relval.add_history('approval', 'succeeded', 'automatic')
      relval_db.save(relval.get_json())
      if exit_code:
        for step in relval.get('steps'):
          step.set('resolved_globaltag', '')
        relval.set('status', 'new')
        relval.add_history('approval', 'failed', 'automatic')
        relval_db.save(relval.get_json())
        return relval
      else:
        print('SUCCESS: ', time.time()-start_time, ' sec')

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
                'voms-proxy-init -voms cms --valid 4:00 --out $(pwd)/proxy.txt']
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
                './config_test_generate.sh']
    start_time = time.time()
    stdout = ssh.execute_command_new(command)
    chunk = ''; x = True; iTime=start_time
    while x:
      line = stdout.readline()
      chunk += line
      if (time.time() - iTime) > 15:
        iTime = time.time()
        self.store_submission_output(relval, str(chunk), None)
        chunk = ''; 
      if not line:
        self.store_submission_output(relval, str(chunk), None)
        x = False
    exit_code = stdout.channel.recv_exit_status()
    self.store_submission_output(relval, None, exit_code)

    return exit_code
