"""
Module that has all classes used for request submission to computing
"""
import json
from uuid import uuid4
from core_lib.utils.ssh_executor import SSHExecutor
from core_lib.utils.locker import Locker
from database.database import Database
from core_lib.utils.submitter import Submitter as BaseSubmitter
from core_lib.utils.common_utils import (get_scram_arch,
                                        run_commands_in_cmsenv)
from core_lib.utils.global_config import Config
from core_lib.utils.emailer import Emailer

class DQMRequestSubmitter(BaseSubmitter):
    """
    Subclass of base submitter that is tailored for RelVal submission
    """

    def add(self, relvalT, relvalR, dqm_pair, target_pair):
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
                         target_pair=target_pair)

    def __handle_error(self, relvalT, relvalR, error_message, error_code):
        """
        Handle error that occured during submission, modify RelVal accordingly
        """
        relval_db = Database('relvals')
        for relval in [relvalT, relvalR]:
            # Remove failed links from DB
            dqm = relval.get('dqm_comparison')
            dqm.pop()
            relval.set('dqm_comparison', dqm)
            relval_db.save(relval.get_json())

        service_url = Config.get('service_url')
        emailer = Emailer()
        prepidT = relvalT.get_prepid()
        prepidR = relvalR.get_prepid()
        Ticket = relvalT.get('jira_ticket')
        subject = f'\U0001F61F | DQM comparison for {Ticket}'
        body = f'Hello,\nUnfortunately submission of DQM comparison job failed. See error log attached.\n'
        body += (f'Target relval: <a href="{service_url}/relvals?prepid={prepidT}">{prepidT}</a>\n')
        body += (f'Reference relval: <a href="{service_url}/relvals?prepid={prepidR}">{prepidR}</a>\n')
        recipients = emailer.get_recipients(relvalT)

        attachment = f'/tmp/attachment_{uuid4()}.txt'
        with open(attachment, 'w') as f:
            f.write(error_message)
        emailer.send_with_mime(subject, body, recipients, attachment=attachment)

    def __handle_success(self, relvalT, relvalR, stdout):
        """
        Handle success of the DQM comparison
        """
        relval_db = Database('relvals')
        for relval in [relvalT, relvalR]:
            dqm = relval.get('dqm_comparison')
            dqm[-1]['status'] = 'compared'
            relval.set('dqm_comparison', dqm)
            relval_db.save(relval.get_json())

        def get_dqm_link(tar, ref, path='relval'):
            dqm_new = relvalT.get('dqm_comparison')[-1]
            tar_run = dqm_new['tar_run'][0]
            ref_run = dqm_new['ref_run'][0]
            tar_data = dqm_new[tar]
            ref_data = dqm_new[ref]
            s1 = f'https://cmsweb.cern.ch/dqm/{path}/start?runnr={tar_run};'
            s2 = f'dataset={tar_data};'
            s3 = 'sampletype=offline_data;filter=all;referencepos=overlay;referenceshow=all;referencenorm=False;'
            s4 = f'referenceobj1=other%3A{ref_run}%3A{ref_data}%3AReference%3A;'
            s5 = 'striptype=object;stripruns=;stripaxis=run;stripomit=none;workspace=Everything;'
            link = s1 + s2 + s3 + s4 + s5
            title = f"Target: {tar_data} Reference: {ref_data}"
            return f"<a href='{link}' title='{title}'>DQM {path}</a>"

        service_url = Config.get('service_url')
        prepidT = relvalT.get_prepid()
        prepidR = relvalR.get_prepid()
        Ticket = relvalT.get('jira_ticket')
        subject = f'\U0001F973 | DQM comparison for {Ticket}'
        compared_link = get_dqm_link('target', 'reference', path='dev')
        original_link = get_dqm_link('source', 'compared_with')
        body = f'Hello,\n DQM comparison is successful. Here are the details\n'
        body += (f'Post comparison link : {compared_link}\n')
        body += (f'Pre comparison link: {original_link}\n')
        body += (f'Target relval: {service_url}/relvals?prepid={prepidT}\n')
        body += (f'Reference relval: {service_url}/relvals?prepid={prepidR}\n')

        attachment = f'/tmp/attachment_{uuid4()}.txt'
        with open(attachment, 'w') as f:
            f.write(stdout)
        emailer = Emailer()
        recipients = emailer.get_recipients(relvalT)
        emailer.send_with_mime(subject, body, recipients, attachment=attachment)

    def create_dqm_comparison(self, relvalT, relvalR, dqm_pair, target_pair):
        """
        Method that is used by submission workers. This is where the actual DQM submission happens
        """
        self.logger.debug('Compare DQM pair:\n%s', json.dumps(dqm_pair, indent=2))
        credentials_file = Config.get('credentials_file')
        # Remember to set WORK directory in worker node
        remote_directory = r'${WORK}/dqm_comparison_submission'
        cmssw_version = dqm_pair['tar_dataset'].split('/')[2].split('-')[0]
        ref_cmssw = dqm_pair['ref_dataset'].split('/')[2].split('-')[0]
        scram_arch = get_scram_arch(cmssw_version)

        data_url = 'https://cmsweb.cern.ch/dqm/relval/data/browse/ROOT/RelValData/'
        tar_run = dqm_pair['tar_run'][0]
        ref_run = dqm_pair['ref_run'][0]
        tar_dataset = dqm_pair['tar_dataset'].replace('/', '__')
        ref_dataset = dqm_pair['ref_dataset'].replace('/', '__')
        tar_file = f'DQM_V0001_R000{tar_run}{tar_dataset}.root'
        ref_file = f'DQM_V0001_R000{ref_run}{ref_dataset}.root'

        wget_options = r'--no-check-certificate '
        wget_options += r'-nd --certificate=${HOME}/.globus/usercert.pem '
        wget_options += r'--certificate-type=PEM '
        wget_options += r'--private-key=${HOME}/.globus/userkey.pem '
        wget_options += r'--private-key-type=PEM '
        tar_prefix   = f'-P "{tar_dataset}" ' + wget_options
        ref_prefix   = f'-P "{ref_dataset}" ' + wget_options

        stript_cmssw_tar = '_'.join(cmssw_version.split('_')[:3]+['x/'])
        stript_cmssw_ref = '_'.join(ref_cmssw.split('_')[:3]+['x/'])
        tar_path = data_url + stript_cmssw_tar + tar_file
        ref_path = data_url + stript_cmssw_ref + ref_file

        #Set home for accessing ssl certs (in Singularity)
        command = [f'export HOME=/afs/cern.ch/user/a/alcauser']
        command += ['set -e']
        command += ['wget -nv -N ' + tar_prefix + tar_path]
        command += ['wget -nv -N ' + ref_prefix + ref_path]

        tar = tar_dataset + '/' + tar_file
        ref = ref_dataset + '/' + ref_file
        newtar_file = f'DQM_V0001_R000{tar_run}{target_pair[0]}.root'
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
            self.logger.info('Locked %s+%s for submission', target_prepid, reference_prepid)
            dqm_script_commands = run_commands_in_cmsenv(command, cmssw_version, scram_arch)
            self.logger.debug('Compare DQM dataset pair command:\n%s', dqm_script_commands)

            ssh = SSHExecutor('lxplus.cern.ch', credentials_file)
            stdout = ssh.execute_command_new([
                                            f'mkdir -p {remote_directory}',
                                            f'cd {remote_directory}', 
                                            dqm_script_commands
                                            ])
            chunk = ''; dummy = True
            while dummy:
                line = stdout.readline()
                chunk += line
                print(line, end='')
                if not line: dummy = False
            exit_code = stdout.channel.recv_exit_status()
            ssh.close_connections()

            if exit_code:
                self.__handle_error(relvalT, relvalR, chunk, exit_code)
            else:
                self.__handle_success(relvalT, relvalR, chunk)
        return tar_run, ref_run
