"""
Module that has all classes used for request submission to computing
"""
import os
import json
import time
from core_lib.utils.ssh_executor import SSHExecutor
from core_lib.utils.locker import Locker
from database.database import Database
from core_lib.utils.connection_wrapper import ConnectionWrapper
from core_lib.utils.submitter import Submitter as BaseSubmitter
from core_lib.utils.common_utils import clean_split, cmssw_setup, dbs_dataset_runs
from core_lib.utils.global_config import Config
from ..utils.emailer import Emailer


class DQMRequestSubmitter(BaseSubmitter):
    """
    Subclass of base submitter that is tailored for RelVal submission
    """

    def add(self, relvalT, relvalR, dqm_pair, relval_controller, target_pair):
        """
        Add a RelVal to the submission queue
        """
        prepidT = relvalT.get_prepid()
        prepidR = relvalR.get_prepid()
        super().add_task(prepidT+prepidR,
                         self.create_dqm_comparison,
                         relvalT=relvalT,
                         relvalR=relvalR,
                         dqm_pair=dqm_pair,
                         controller=relval_controller,
                         target_pair=target_pair)

    def __handle_error(self, relvalT, relvalR, error_message):
        """
        Handle error that occured during submission, modify RelVal accordingly
        """
        self.logger.error(error_message)
        relval_db = Database('relvals')
        for relval in [relvalT, relvalR]:
            dqm = relval.get('dqm_comparison')
            dqm.pop()
            relval.set('dqm_comparison', dqm)
            relval_db.save(relval.get_json())

        service_url = Config.get('service_url')
        emailer = Emailer()
        prepidT = relvalT.get_prepid()
        prepidR = relvalR.get_prepid()
        subject = f'DQM comparison submission failed {prepidT}, {prepidR}'
        body = f'Hello,\n\nUnfortunately submission of DQM comparison job failed.\n'
        body += (f'Target relval: {service_url}/relvals?prepid={prepidT}\n')
        body += (f'Reference relval: {service_url}/relvals?prepid={prepidR}\n')
        # body += f'Error message:\n\n{error_message}'
        recipients = emailer.get_recipients(relvalT)
        self.__send_email(repr(subject), repr(body), recipients, attach=error_message)

    def __handle_success(self, relvalT, relvalR):
        """
        Handle notification of successful submission
        """
        prepid = relval.get_prepid()
        last_workflow = relval.get('workflows')[-1]['name']
        cmsweb_url = Config.get('cmsweb_url')
        self.logger.info('Submission of %s succeeded', prepid)
        service_url = Config.get('service_url')
        emailer = Emailer()
        subject = f'RelVal {prepid} submission succeeded'
        body = f'Hello,\n\nSubmission of {prepid} succeeded.\n'
        body += (f'You can find this relval at '
                 f'{service_url}/relvals?prepid={prepid}\n')
        body += f'Workflow in ReqMgr2 {cmsweb_url}/reqmgr2/fetch?rid={last_workflow}'
        # if Config.get('development'):
        #     body += '\nNOTE: This was submitted from a development instance of RelVal machine '
        #     body += 'and this job will never start running in computing!\n'

        recipients = emailer.get_recipients(relval)
        self.__send_email(repr(subject), repr(body), recipients)

    def __send_email(self, subject, body, recipients, attach=None):
        credentials_file = Config.get('credentials_file')
        remote_directory = Config.get('remote_path').rstrip('/')
        if attach:
            f = open('/tmp/attachment.txt', 'w')
            f.write(attach)
        with SSHExecutor('lxplus.cern.ch', credentials_file) as ssh:
            ssh.upload_file('/tmp/attachment.txt', f'{remote_directory}/attachment.txt')
            ssh.upload_file('./core_lib/utils/emailer.py', f'{remote_directory}/emailer.py')
            command = [f'cd {remote_directory}']
            command.append(f"""python3 -c "from emailer import Emailer; emailer = Emailer(); \
                        emailer.send(str({subject}), str({body}), {recipients}, attach=True)" || exit $? """)
            stdout, stderr, exit_code = ssh.execute_command(command)
            if exit_code != 0:
                self.logger.error('Error sending email:\nstdout:%s\nstderr:%s',
                                  stdout,
                                  stderr)

    def create_dqm_comparison(self, relvalT, relvalR, dqm_pair, controller, target_pair):
        """
        Method that is used by submission workers. This is where the actual DQM submission happens
        """
        self.logger.debug('Compare DQM pair:\n%s', json.dumps(dqm_pair, indent=2))
        credentials_file = Config.get('credentials_file')
        # Remember to set WORK directory in worker node
        remote_directory = r'${WORK}/dqm_comparison_submission'
        command = [f'cd {remote_directory}']
        cmssw_version = dqm_pair['target_dataset'].split('/')[2].split('-')[0]
        ref_cmssw = dqm_pair['reference_dataset'].split('/')[2].split('-')[0]

        command.extend(cmssw_setup('CMSSW_12_3_3').split('\n'))

        data_url = 'https://cmsweb.cern.ch/dqm/relval/data/browse/ROOT/RelValData/'
        target_run = dbs_dataset_runs(dqm_pair['target_dataset'])[0]
        ref_run = dbs_dataset_runs(dqm_pair['reference_dataset'])[0]
        target_dataset = dqm_pair['target_dataset'].replace('/', '__')
        reference_dataset = dqm_pair['reference_dataset'].replace('/', '__')
        target_file = f'DQM_V0001_R000{target_run}{target_dataset}.root'
        ref_file = f'DQM_V0001_R000{ref_run}{reference_dataset}.root'

        wget_options = r'-nd --certificate=${HOME}/.globus/usercert.pem '
        wget_options += r'--certificate-type=PEM '
        wget_options += r'--private-key=${HOME}/.globus/userkey.pem '
        wget_options += r'--private-key-type=PEM '
        target_prefix = f'-P {target_dataset} ' + wget_options
        ref_prefix = f'-P {reference_dataset} ' + wget_options

        stript_cmssw = '_'.join(cmssw_version.split('_')[:3]+['x/'])
        stript_cmssw_ref = '_'.join(ref_cmssw.split('_')[:3]+['x/'])
        target_path = data_url + stript_cmssw + target_file
        ref_path = data_url+ stript_cmssw_ref + ref_file

        command += ['wget -nv -N ' + target_prefix + target_path]
        command += ['wget -nv -N ' + ref_prefix + ref_path]

        tar = target_dataset + '/' + target_file
        ref = reference_dataset + '/' + ref_file
        newtar_file = f'DQM_V0001_R000{target_run}{target_pair[0]}.root'
        newref_file = f'DQM_V0001_R000{ref_run}{target_pair[1]}.root'
        command += [f'./compareHistograms.py -p {tar} -b {ref} --new-target {target_pair[0]} --ref-target {target_pair[1]}']
        file = f'dqmHistoComparisonOutput/pr/{newtar_file}'
        command += [f'visDQMUpload.py https://cmsweb.cern.ch/dqm/dev {file}']
        file = f'dqmHistoComparisonOutput/base/{newref_file}'
        command += [f'visDQMUpload.py https://cmsweb.cern.ch/dqm/dev {file}']
 
        target_prepid = relvalT.get_prepid()
        reference_prepid = relvalR.get_prepid()
        self.logger.debug('Will try to acquire lock for %s and %s' %(target_prepid, reference_prepid))
        with Locker().get_lock('+'.join([target_prepid, reference_prepid])):
            # with Locker().get_lock():
            relval_db = Database('relvals')
            self.logger.info('Locked %s+%s for submission', target_prepid, reference_prepid)

            self.logger.debug('Compare DQM dataset pair command:\n%s', '\n'.join(command))
            try:
                with SSHExecutor('lxplus.cern.ch', credentials_file) as ssh_executor:
                    stdout, stderr, exit_code = ssh_executor.execute_command(f'mkdir -p {remote_directory}')
                    if exit_code != 0:
                        self.logger.error('Error creating %s:\nstdout:%s\nstderr:%s',
                                          remote_directory,
                                          stdout,
                                          stderr)
                        raise Exception(f'Error creting remote directory: {stderr}')

                    stdout, stderr, exit_code = ssh_executor.execute_command(command)
                    if exit_code != 0:
                        self.logger.error('Error creating comparison plots:\nstdout:%s\nstderr:%s',
                                          stdout,
                                          stderr)
                        raise Exception(f'Error creating comparison plots: {stderr}')

                iterables = zip([dqm_pair['target_dataset'], dqm_pair['reference_dataset']], [relvalT, relvalR])
                for dataset, relval in iterables:
                    dqm = relval.get('dqm_comparison')
                    dqm[-1]['status'] = 'compared'
                    relval.set('dqm_comparison', dqm)
                    relval_db.save(relval.get_json())

            except Exception as ex:
                self.__handle_error(relvalT, relvalR, str(ex))
                return

            # self.__handle_success(relvalT, relvalR)
        return target_run, ref_run