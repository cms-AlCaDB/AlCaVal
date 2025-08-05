"""
Module that contains RelValController class
"""
import json
import time
import random
import requests
from api.utils.relval_test_submitter import RelvalTestSubmitter
from database.database import Database
from core_lib.controller.controller_base import ControllerBase
from core_lib.utils.ssh_executor import SSHExecutor
from core_lib.utils.global_config import Config
from core_lib.utils.common_utils import (clean_split,
                                         cmsweb_reject_workflows,
                                         config_cache_lite_setup,
                                         dbs_datasetlist, get_hash, get_workflows_from_reqmgr2,
                                         get_workflows_from_reqmgr2_for_prepid,
                                         run_commands_in_cmsenv,
                                         dbs_dataset_runs)
from resources.smart_tricks import check_if_dataset_exists
from ..utils.submitter import RequestSubmitter
from ..utils.dqm_submitter import DQMRequestSubmitter
from ..model.ticket import Ticket
from ..model.relval import RelVal
from ..model.relval_step import RelValStep


DEAD_WORKFLOW_STATUS = {'rejected', 'aborted', 'failed', 'rejected-archived',
                        'aborted-archived', 'failed-archived', 'aborted-completed'}


class RelValController(ControllerBase):
    """
    RelVal controller performs all actions with RelVal objects
    """

    def __init__(self):
        ControllerBase.__init__(self)
        self.database_name = 'relvals'
        self.model_class = RelVal

    def create(self, json_data, condition_name=''):
        cmssw_release = json_data.get('cmssw_release')
        batch_name = json_data.get('batch_name')
        # Use workflow name for prepid if possible, if not - first step name
        if json_data.get('workflow_name'):
            workflow_name = json_data['workflow_name']
        else:
            first_step = RelValStep(json_input=json_data.get('steps')[0])
            workflow_name = first_step.get_short_name()
            json_data['workflow_name'] = workflow_name

        condition_name = f'{condition_name}-' if condition_name else ''
        prepid_part = f'{cmssw_release}__{batch_name}-{condition_name}{workflow_name}'.strip('-_')
        json_data['prepid'] = f'{prepid_part}-00000'
        relval_db = Database('relvals')
        with self.locker.get_lock(f'generate-relval-prepid-{prepid_part}'):
            # Get a new serial number
            serial_number = self.get_highest_serial_number(relval_db,
                                                           f'{prepid_part}-*')
            serial_number += 1
            # Form a new temporary prepid
            prepid = f'{prepid_part}-{serial_number:05d}'
            json_data['prepid'] = prepid
            relval = super().create(json_data)

        return relval

    def after_update(self, old_obj, new_obj, changed_values):
        self.logger.info('Changed values: %s', changed_values)
        if 'workflow_name' in changed_values:
            new_relval = self.create(new_obj.get_json())
            old_prepid = old_obj.get_prepid()
            new_prepid = new_relval.get_prepid()
            new_relval.set('history', old_obj.get('history'))
            new_relval.add_history('rename', [old_prepid, new_prepid], None)
            relvals_db = Database('relvals')
            relvals_db.save(new_relval.get_json())
            self.logger.info('Created %s as rename of %s', new_prepid, old_prepid)
            new_obj.set('prepid', new_prepid)
            # Update the ticket...
            tickets_db = Database('tickets')
            tickets = tickets_db.query(f'created_relvals={old_obj.get_prepid()}')
            self.logger.debug(json.dumps(tickets, indent=2))
            for ticket_json in tickets:
                ticket_prepid = ticket_json['prepid']
                with self.locker.get_lock(ticket_prepid):
                    ticket_json = tickets_db.get(ticket_prepid)
                    ticket = Ticket(json_input=ticket_json)
                    created_relvals = ticket.get('created_relvals')
                    if old_prepid in created_relvals:
                        created_relvals.remove(old_prepid)

                    created_relvals.append(new_prepid)
                    ticket.set('created_relvals', created_relvals)
                    ticket.add_history('rename', [old_prepid, new_prepid], None)
                    tickets_db.save(ticket.get_json())

            self.delete(old_obj.get_json())

    def get_editing_info(self, obj):
        editing_info = super().get_editing_info(obj)
        prepid = obj.get_prepid()
        status = obj.get('status')
        is_new = status == 'new'
        creating_new = not bool(prepid)
        editing_info['prepid'] = False
        editing_info['batch_name'] = creating_new
        editing_info['campaign_timestamp'] = False
        editing_info['cmssw_release'] = creating_new
        editing_info['jira_ticket'] = True
        editing_info['cpu_cores'] = is_new
        editing_info['fragment'] = is_new
        editing_info['job_dict_overwrite'] = is_new
        editing_info['memory'] = is_new
        editing_info['label'] = is_new
        editing_info['notes'] = True
        editing_info['matrix'] = creating_new
        editing_info['sample_tag'] = is_new
        editing_info['scram_arch'] = is_new
        editing_info['hlt_menu'] = is_new
        editing_info['size_per_event'] = is_new
        editing_info['time_per_event'] = is_new
        editing_info['workflow_id'] = False
        editing_info['workflow_name'] = is_new
        editing_info['steps'] = is_new
        editing_info['dqm_comparison'] = True

        return editing_info

    def after_delete(self, obj):
        prepid = obj.get_prepid()
        tickets_db = Database('tickets')
        tickets = tickets_db.query(f'created_relvals={prepid}')
        self.logger.debug(json.dumps(tickets, indent=2))
        for ticket_json in tickets:
            ticket_prepid = ticket_json['prepid']
            with self.locker.get_lock(ticket_prepid):
                ticket_json = tickets_db.get(ticket_prepid)
                ticket = Ticket(json_input=ticket_json)
                created_relvals = ticket.get('created_relvals')
                if prepid in created_relvals:
                    created_relvals.remove(prepid)

                ticket.set('created_relvals', created_relvals)
                ticket.add_history('remove_relval', prepid, None)
                tickets_db.save(ticket.get_json())

    def get_cmsdriver(self, relval, for_submission=False):
        """
        Get bash script with cmsDriver commands for a given RelVal
        If script will be used for submission, replace input file with placeholder
        """
        self.logger.debug('Getting cmsDriver commands for %s', relval.get_prepid())
        cms_driver = '#!/bin/bash\n\n'
        cms_driver += 'export SINGULARITY_CACHEDIR="/tmp/$(whoami)/singularity"\n'
        cms_driver += '\n'
        cms_driver += relval.get_cmsdrivers(for_submission)
        cms_driver += '\n\n'

        return cms_driver

    def get_cmsdriver_test(self, relval):
        """
        Get bash script with cmsDriver commands for test. 
        It will test commands locally and provide a job report.
        """
        self.logger.debug('Getting cmsDriver commands for testing for %s', relval.get_prepid())
        cms_driver_test = '#!/bin/bash\n\n'
        cms_driver_test += 'export SINGULARITY_CACHEDIR="/tmp/$(whoami)/singularity"\n'
        cms_driver_test += '\n'
        cms_driver_test += relval.get_cmsdrivers_test()
        cms_driver_test += '\n\n'

        return cms_driver_test

    def get_config_upload_file(self, relval):
        """
        Get bash script that would upload config files to ReqMgr2
        """
        self.logger.debug('Getting config upload script for %s', relval.get_prepid())
        database_url = Config.get('cmsweb_url').replace('https://', '').replace('http://', '')
        bash = ['#!/bin/bash',
                '']

        steps = relval.get('steps')
        # Check if all expected config files are present
        for step in steps:
            config_name = step.get_config_file_name()
            if config_name:
                bash += [f'if [ ! -s "{config_name}.py" ]; then',
                         f'  echo "File {config_name}.py is missing" >&2',
                         '  exit 1',
                         'fi',
                         '']

        # Use ConfigCacheLite and TweakMakerLite instead of WMCore
        bash += config_cache_lite_setup().split('\n')
        bash += ['']

        previous_cmssw = None
        previous_scram = None
        # Remove trailing steps with no config gile names
        while steps and not steps[-1].get_config_file_name():
            steps = steps[:-1]

        commands = []
        for step in steps:
            # Run config uploader
            config_name = step.get_config_file_name()
            if not config_name:
                continue

            step_cmssw = step.get_release()
            scram_arch = step.get_scram_arch()
            if commands and (step_cmssw != previous_cmssw or scram_arch != previous_scram):
                commands += ['']
                bash += run_commands_in_cmsenv(commands, previous_cmssw, previous_scram).split('\n')
                commands = []

            commands.append(('$PYTHON_INT config_uploader.py '
                             f'--file $(pwd)/{config_name}.py '
                             f'--label {config_name} '
                             '--group ppd '
                             '--user $(echo $USER) '
                             f'--db {database_url} || exit $?'))

            previous_cmssw = step_cmssw
            previous_scram = scram_arch

        if commands:
            commands += ['']
            bash += run_commands_in_cmsenv(commands, previous_cmssw, previous_scram).split('\n')

        return '\n'.join(bash)

    def get_task_dict(self, relval, step, step_index):
        #pylint: disable=too-many-statements
        """
        Return a dictionary for single task of ReqMgr2 dictionary
        """
        self.logger.debug('Getting step %s dict for %s', step_index, relval.get_prepid())
        task_dict = {}
        # If it's firtst step and not input file - it is generator
        # set Seeding to AutomaticSeeding, RequestNumEvets, EventsPerJob and EventsPerLumi
        # It expects --relval attribute
        if step_index == 0:
            task_dict['Seeding'] = 'AutomaticSeeding'
            task_dict['PrimaryDataset'] = relval.get_primary_dataset()
            requested_events, events_per_job = step.get_relval_events()
            events_per_lumi = step.get('events_per_lumi')
            task_dict['RequestNumEvents'] = requested_events
            task_dict['SplittingAlgo'] = 'EventBased'
            task_dict['EventsPerJob'] = events_per_job
            if events_per_lumi:
                # EventsPerLumi has to be <= EventsPerJob
                task_dict['EventsPerLumi'] = min(int(events_per_lumi), int(events_per_job))
            else:
                task_dict['EventsPerLumi'] = int(events_per_job)
        else:
            input_step = relval.get('steps')[step.get_input_step_index()]
            if input_step.get_step_type() == 'input_file':
                input_dict = input_step.get('input')
                # Input file step is not a task
                # Use this as input in next step
                task_dict['InputDataset'] = input_dict['dataset']
                if input_dict['lumisection']:
                    task_dict['LumiList'] = input_dict['lumisection']
                elif input_dict['run']:
                    task_dict['RunWhitelist'] = [int(run) for run in input_dict['run']]
            else:
                task_dict['InputTask'] = input_step.get_short_name()
                _, input_module = step.get_input_eventcontent(input_step)
                task_dict['InputFromOutputModule'] = f'{input_module}output'

            if step.get('lumis_per_job') != '':
                task_dict['LumisPerJob'] = int(step.get('lumis_per_job'))

            task_dict['SplittingAlgo'] = 'LumiBased'

        task_dict['TaskName'] = step.get_short_name()
        task_dict['ConfigCacheID'] = step.get('config_id')
        task_dict['KeepOutput'] = step.get('keep_output')
        task_dict['ScramArch'] = step.get_scram_arch()
        resolved_globaltag = step.get('resolved_globaltag')
        if resolved_globaltag:
            task_dict['GlobalTag'] = resolved_globaltag

        processing_string = relval.get_processing_string(step_index)
        if processing_string:
            task_dict['ProcessingString'] = processing_string

        task_dict['CMSSWVersion'] = step.get_release()
        task_dict['AcquisitionEra'] = task_dict['CMSSWVersion']
        task_dict['Memory'] = relval.get('memory')
        task_dict['Multicore'] = relval.get('cpu_cores')
        task_dict['TimePerEvent'] = step.get('time_per_event')
        task_dict['SizePerEvent'] = step.get('size_per_event')
        task_dict['Campaign'] = relval.get_campaign()
        driver = step.get('driver')
        if driver.get('nStreams'):
            task_dict['EventStreams'] = int(driver['nStreams'])

        if driver.get('pileup_input'):
            task_dict['MCPileup'] = driver['pileup_input']
            while task_dict['MCPileup'][0] != '/':
                task_dict['MCPileup'] = task_dict['MCPileup'][1:]

        if step.get_gpu_requires() != 'forbidden':
            task_dict['GPUParams'] = json.dumps(step.get_gpu_dict(), sort_keys=True)
            task_dict['RequiresGPU'] = step.get_gpu_requires()

        return task_dict

    def get_job_dict(self, relval):
        #pylint: disable=too-many-statements
        """
        Return a dictionary for ReqMgr2
        """
        prepid = relval.get_prepid()
        self.logger.debug('Getting job dict for %s', prepid)
        job_dict = {}
        job_dict['Group'] = 'PPD'
        job_dict['Requestor'] = 'alcadb.user'
        job_dict['CouchURL'] = Config.get('cmsweb_url') + '/couchdb'
        job_dict['ConfigCacheUrl'] = job_dict['CouchURL']
        job_dict['PrepID'] = prepid
        job_dict['SubRequestType'] = 'RelVal'
        job_dict['RequestString'] = relval.get_request_string()
        job_dict['Campaign'] = relval.get_campaign()
        job_dict['RequestPriority'] = random.randrange(800000, 900000, 5000)
        job_dict['TimePerEvent'] = relval.get('time_per_event')
        job_dict['SizePerEvent'] = relval.get('size_per_event')
        job_dict['ProcessingVersion'] = 1
        # Harvesting should run on single core with 3GB memory,
        # and each task will have it's own core and memory setting
        job_dict['Memory'] = 3000
        job_dict['Multicore'] = 1
        job_dict['EnableHarvesting'] = False
        # Set DbsUrl differently for dev and prod versions
        # "URL to the DBS instance where the input data is registered"
        if not Config.get('development'):
            job_dict['DbsUrl'] = 'https://cmsweb-prod.cern.ch/dbs/prod/global/DBSReader'
        else:
            # https://cmsweb-testbed.cern.ch/dbs/int/global/DBSReader
            job_dict['DbsUrl'] = 'https://cmsweb-prod.cern.ch/dbs/prod/global/DBSReader'

        task_number = 0
        input_step = None
        global_dict_step = None
        for step_index, step in enumerate(relval.get('steps')):
            # If it's input file, it's not a task
            if step.get_step_type() == 'input_file':
                input_step = step
                continue

            if not global_dict_step:
                global_dict_step = step

            # Handle harvesting step quickly
            if step.has_step('HARVESTING'):
                # It is harvesting step
                # It goes in the main job_dict
                job_dict['DQMConfigCacheID'] = step.get('config_id')
                job_dict['EnableHarvesting'] = True
                if not Config.get('development'):
                    # Do not upload to prod DQM GUI in dev
                    job_dict['DQMUploadUrl'] = 'https://cmsweb.cern.ch/dqm/relval'
                else:
                    # Upload to some dev DQM GUI
                    job_dict['DQMUploadUrl'] = 'https://cmsweb-testbed.cern.ch/dqm/dev'

                continue

            # Add task to main dict
            task_number += 1
            job_dict[f'Task{task_number}'] = self.get_task_dict(relval, step, step_index)

        # Set values to the main dictionary
        if global_dict_step:
            job_dict['CMSSWVersion'] = global_dict_step.get_release()
            job_dict['ScramArch'] = global_dict_step.get_scram_arch()
            job_dict['AcquisitionEra'] = job_dict['CMSSWVersion']
            resolved_globaltag = global_dict_step.get('resolved_globaltag')
            if resolved_globaltag:
                job_dict['GlobalTag'] = resolved_globaltag

            global_step_index = global_dict_step.get_index_in_parent()
            processing_string = relval.get_processing_string(global_step_index)
            if processing_string:
                job_dict['ProcessingString'] = processing_string

        if task_number > 0:
            # At least one task - TaskChain workflow
            job_dict['RequestType'] = 'TaskChain'
            job_dict['TaskChain'] = task_number

        elif global_dict_step:
            # Only harvesting step - DQMHarvest workflow
            job_dict['RequestType'] = 'DQMHarvest'
            if input_step:
                input_dict = input_step.get('input')
                job_dict['InputDataset'] = input_dict['dataset']
                if input_dict['lumisection']:
                    job_dict['LumiList'] = input_dict['lumisection']
                elif input_dict['run']:
                    job_dict['RunWhitelist'] = [int(run) for run in input_dict['run']]

        job_dict_overwrite = relval.get('job_dict_overwrite')
        if job_dict_overwrite:
            self.logger.info('Overwriting job dict for %s with %s', prepid, job_dict_overwrite)
            self.apply_job_dict_overwrite(job_dict, job_dict_overwrite)

        return job_dict

    def apply_job_dict_overwrite(self, job_dict, overwrite):
        """
        Apply overwrites to job dictionary
        """
        for key, value in overwrite.items():
            obj = job_dict
            key_parts = key.split('.')
            for part in key_parts[:-1]:
                if part in obj:
                    obj = obj[part]
                else:
                    break
            else:
                obj[key_parts[-1]] = value


    def resolve_auto_conditions(self, conditions_tree):
        """
        Iterate through conditions tree and resolve global tags
        Conditions tree example:
        {
            "CMSSW_11_2_0_pre9": {
                "slc7_a_b_c": {
                    "auto:phase1_2021_realistic": None
                }
            }
        }
        """
        self.logger.debug('Resolve auto conditions of:\n%s', json.dumps(conditions_tree, indent=2))
        credentials_file = Config.get('credentials_file')
        remote_directory = Config.get('remote_path').rstrip('/')
        resolve_command = []
        for cmssw_version, scram_tree in conditions_tree.items():
            for scram_arch, conditions in scram_tree.items():
                conditions_str = ','.join(list(conditions.keys()))
                resolve_command += run_commands_in_cmsenv(['$PYTHON_INT resolve_auto_global_tag.py '
                                                           f'"{cmssw_version}" '
                                                           f'"{scram_arch}" '
                                                           f'"{conditions_str}" || exit $?'],
                                                          cmssw_version,
                                                          scram_arch).split('\n')

        self.logger.debug('Resolve auto conditions command:\n%s', '\n'.join(resolve_command))
        with SSHExecutor('lxplus.cern.ch', credentials_file) as ssh_executor:
            # Upload python script to resolve auto globaltag by upload script
            stdout, stderr, exit_code = ssh_executor.execute_command(f'mkdir -p {remote_directory}')
            if exit_code != 0:
                self.logger.error('Error creating %s:\nstdout:%s\nstderr:%s',
                                  remote_directory,
                                  stdout,
                                  stderr)
                raise Exception(f'Error creting remote directory: {stderr}')

            ssh_executor.upload_file('./api/utils/resolve_auto_global_tag.py',
                                     f'{remote_directory}/resolve_auto_global_tag.py')
            script_name = f'resolve_{get_hash(resolve_command)}.sh'
            ssh_executor.upload_as_file('\n'.join(resolve_command),
                                        f'{remote_directory}/{script_name}')
            command = [f'cd {remote_directory}',
                       f'chmod +x {script_name}',
                       f'./{script_name}',
                       f'rm {script_name}']
            stdout, stderr, exit_code = ssh_executor.execute_command(command)
            if exit_code != 0:
                self.logger.error('Error resolving auto global tags:\nstdout:%s\nstderr:%s',
                                  stdout,
                                  stderr)
                raise Exception(f'Error resolving auto globaltags: {stderr}')

        tags = [x for x in clean_split(stdout, '\n') if x.startswith('GlobalTag:')]
        for resolved_tag in tags:
            split_resolved_tag = clean_split(resolved_tag, ' ')
            cmssw_version = split_resolved_tag[1]
            scram_arch = split_resolved_tag[2]
            conditions = split_resolved_tag[3]
            resolved = split_resolved_tag[4]
            self.logger.debug('Resolved %s to %s in %s (%s)',
                              conditions,
                              resolved,
                              cmssw_version,
                              scram_arch)
            conditions_tree[cmssw_version][scram_arch][conditions] = resolved

    def get_default_step(self):
        """
        Get a default empty RelVal step
        """
        self.logger.info('Getting a default RelVal step')
        step = RelValStep.schema()
        return step

    def update_status(self, relval, status, timestamp=None):
        """
        Set new status to RelVal, update history accordingly and save to database
        """
        relval_db = Database(self.database_name)
        relval.set('status', status)
        relval.add_history('status', status, None, timestamp)
        relval_db.save(relval.get_json())
        self.logger.info('Set "%s" status to "%s"', relval.get_prepid(), status)

    def next_status(self, relvals):
        """
        Trigger list of RelVals to move to next status
        """
        by_status = {}
        for relval in relvals:
            status = relval.get('status')
            if status not in by_status:
                by_status[status] = []

            by_status[status].append(relval)

        results = []
        for status, relvals_with_status in by_status.items():
            self.logger.info('%s RelVals with status %s', len(relvals_with_status), status)
            if status == 'new':
                results.extend(self.move_relvals_to_approving(relvals_with_status))

            elif status == 'approving':
                raise Exception('Cannot move RelVals that are being approved to next status')

            elif status == 'approved':
                results.extend(self.move_relvals_to_submitting(relvals_with_status))

            elif status == 'submitting':
                raise Exception('Cannot move RelVals that are being submitted to next status')

            elif status == 'submitted':
                results.extend(self.move_relvals_to_done(relvals_with_status))

            elif status == 'done':
                raise Exception('Cannot move RelVals that are already done to next status')

            elif status == 'archived':
                # Attempt to move relvals to "done" in case they were "fixed"
                results.extend(self.move_relvals_to_done(relvals_with_status))

        return results

    def previous_status(self, relval):
        """
        Trigger RelVal to move to previous status
        """
        prepid = relval.get_prepid()
        with self.locker.get_nonblocking_lock(prepid):
            if relval.get('status') == 'approving':
                self.move_relval_back_to_new(relval)
            if relval.get('status') == 'approved':
                self.move_relval_back_to_new(relval)
            elif relval.get('status') == 'submitting':
                self.move_relval_back_to_approved(relval)
            elif relval.get('status') == 'submitted':
                self.move_relval_back_to_approved(relval)
            elif relval.get('status') in ('done', 'archived'):
                self.move_relval_back_to_approved(relval)
                self.move_relval_back_to_new(relval)

        return relval

    def get_resolved_conditions(self, relvals):
        """
        Get a dictionary of dicitonaries of resolved auto: conditions
        """
        conditions_tree = {}
        # Collect auto: conditions by CMSSW release
        for relval in relvals:
            if relval.get('status') != 'new':
                continue

            for step in relval.get('steps'):
                if step.get_step_type() != 'cms_driver':
                    # Collect only driver steps that have conditions
                    continue

                conditions = step.get('driver')['conditions']
                if not conditions.startswith('auto:'):
                    # Collect only auto: ... conditions
                    continue

                cmssw = step.get_release()
                scram = step.get_scram_arch()
                conditions_tree.setdefault(cmssw, {}).setdefault(scram, {})[conditions] = None

        # Resolve auto:conditions to actual globaltags
        self.resolve_auto_conditions(conditions_tree)
        return conditions_tree

    def get_optimal_parameters(self, relval):
        """Do local testing and fetch optimal parameters for submission"""
        tickets_db = Database('tickets')
        tickets = tickets_db.query(f'created_relvals={relval.get_prepid()}')
        ticket_note = tickets[0].get('notes') if tickets else ''
        relval_note = relval.get('notes')
        ticket_note = ticket_note.strip().startswith('Skip local test')
        relval_note = relval_note.strip().startswith('Skip local test')
        skip_test = relval_note or ticket_note
        if not skip_test:
            RelvalTestSubmitter().add(relval, self)
        return skip_test

    def move_relvals_to_approving(self, relvals):
        """
        Try to move RelVals to approving status
        """
        # Check if all necessary GPU parameters are set
        for relval in relvals:
            prepid = relval.get_prepid()
            for index, step in enumerate(relval.get('steps')):
                if step.get_gpu_requires() != 'forbidden':
                    gpu_dict = step.get('gpu')
                    if not gpu_dict.get('gpu_memory'):
                        raise Exception(f'GPU Memory not set in {prepid} step {index + 1}')

                    if not gpu_dict.get('cuda_capabilities'):
                        raise Exception(f'CUDA Capabilities not set in {prepid} step {index + 1}')

                    if not gpu_dict.get('cuda_runtime'):
                        raise Exception(f'GPU Runtime not set in {prepid} step {index + 1}')

            # Check existance of dataset and runs and if they have enough events
            for step in relval.get('steps'):
                if step.get_step_type() == 'input_file':
                    dataset = step.get('input').get('dataset')
                    runsLs = set(step.get('input').get('lumisection').keys())
                    runs = set(step.get('input').get('run'))
            ds_runs = dbs_dataset_runs(dataset)
            db_runs = {int(run) for run in runs or runsLs}
            if not set(ds_runs).intersection(db_runs):
                raise Exception(f'Runs {", ".join(runs or runsLs)} are not there in the dataset {dataset}')

        conditions_tree = self.get_resolved_conditions(relvals)
        results = []
        # Go through relvals and set resolved globaltags from the updated dict
        for relval in relvals:
            prepid = relval.get_prepid()
            with self.locker.get_nonblocking_lock(prepid):
                for step in relval.get('steps'):
                    if step.get_step_type() != 'cms_driver':
                        # Collect only driver steps that have conditions
                        continue

                    conditions = step.get('driver')['conditions']
                    if conditions.startswith('auto:'):
                        cmssw = step.get_release()
                        scram = step.get_scram_arch()
                        resolved_conditions = conditions_tree[cmssw][scram][conditions]
                        step.set('resolved_globaltag', resolved_conditions)
                    else:
                        step.set('resolved_globaltag', conditions)
                # Perform local test and fetch optimal params for submission
                test_skipped = self.get_optimal_parameters(relval)
                if test_skipped:
                    self.update_status(relval, 'approved')
                else:
                    self.update_status(relval, 'approving')
                results.append(relval)

        return results

    def get_dataset_access_types(self, relvals):
        """
        Return a dictionary of dataset access types
        """
        dataset_access_types = {}
        datasets_to_check = set()
        for relval in relvals:
            for step in relval.get('steps'):
                if step.get_step_type() == 'input_file':
                    dataset = step.get('input')['dataset']
                elif step.get('driver')['pileup_input']:
                    dataset = step.get('driver')['pileup_input']
                else:
                    continue

                dataset = dataset[dataset.index('/'):]
                datasets_to_check.add(dataset)

        if not datasets_to_check:
            return {}

        dbs_datasets = dbs_datasetlist(list(datasets_to_check))
        for dataset in dbs_datasets:
            dataset_name = dataset['dataset']
            if dataset_name not in datasets_to_check:
                continue

            access_type = dataset.get('dataset_access_type', 'unknown')
            datasets_to_check.remove(dataset_name)
            dataset_access_types[dataset_name] = access_type

        if datasets_to_check:
            datasets_to_check = ', '.join(list(datasets_to_check))
            raise Exception(f'Could not get status for datasets: {datasets_to_check}')

        return dataset_access_types

    def move_relvals_to_submitting(self, relvals):
        """
        Try to add RelVals to submission queue and get sumbitted
        """
        results = []
        dataset_access_types = self.get_dataset_access_types(relvals)
        for relval in relvals:
            prepid = relval.get_prepid()
            with self.locker.get_nonblocking_lock(prepid):
                batch_name = relval.get('batch_name')
                cmssw_release = relval.get('cmssw_release')
                relval_db = Database('relvals')
                # Make sure all datasets are VALID in DBS
                steps = relval.get('steps')
                for step in steps:
                    if step.get_step_type() == 'input_file':
                        dataset = step.get('input')['dataset']
                    elif step.get('driver')['pileup_input']:
                        dataset = step.get('driver')['pileup_input']
                    else:
                        continue

                    dataset = dataset[dataset.index('/'):]
                    access_type = dataset_access_types[dataset]
                    if access_type.lower() != 'valid':
                        raise Exception(f'{dataset} type is {access_type}, it must be VALID')

                # Create or find campaign timestamp
                # Threshold in seconds
                threshold = 3600
                locker_key = f'move-relval-to-submitting-{cmssw_release}__{batch_name}'
                with self.locker.get_lock(locker_key):
                    now = int(time.time())
                    # Get RelVal with newest timestamp in this campaign (CMSSW + Batch Name)
                    db_query = f'cmssw_release={cmssw_release}&&batch_name={batch_name}'
                    relvals_with_timestamp = relval_db.query(db_query,
                                                             limit=1,
                                                             sort_attr='campaign_timestamp',
                                                             sort_asc=False)
                    newest_timestamp = 0
                    if relvals_with_timestamp:
                        newest_timestamp = relvals_with_timestamp[0].get('campaign_timestamp', 0)

                    self.logger.info('Newest timestamp for %s__%s is %s (%s), threshold is %s',
                                     cmssw_release,
                                     batch_name,
                                     newest_timestamp,
                                     (newest_timestamp - now),
                                     threshold)
                    if newest_timestamp == 0 or newest_timestamp < now - threshold:
                        newest_timestamp = now

                    self.logger.info('Campaign timestamp for %s__%s will be set to %s',
                                     cmssw_release,
                                     batch_name,
                                     newest_timestamp)
                    relval.set('campaign_timestamp', newest_timestamp)
                    self.update_status(relval, 'submitting')

                RequestSubmitter().add(relval, self)
                results.append(relval)

        return results

    def move_relvals_to_done(self, relvals):
        """
        Try to move RelVal to done or archived status
        """
        results = []
        # RelVal will not have recoveries, so "completed" is the last state
        done_status = ('completed', )
        archived_status = ('normal-archived', 'rejected-archived', 'aborted-archived')
        # Archived threshold - if workflow is archived for more than a week, but
        # is not done normally (VALID datasets) - move it to 'archived' status
        archived_threshold = time.time() - 7 * 24 * 3600
        for relval in relvals:
            prepid = relval.get_prepid()
            with self.locker.get_nonblocking_lock(prepid):
                relval = self.update_workflows(relval)
                workflows = relval.get('workflows')
                workflows = [w for w in workflows if w['type'].lower() != 'resubmission']
                if not workflows:
                    raise Exception(f'{prepid} does not have any workflows in computing')

                last_workflow = workflows[-1]
                datasets = last_workflow['output_datasets']
                status_history = last_workflow['status_history']
                # Get all not-VALID datasets
                not_valid_datasets = [d['name'] for d in datasets if d['type'].lower() != 'valid']
                # Get time when workflow became completed
                completed_timestamp = None
                for status in status_history:
                    if status['status'] in done_status:
                        completed_timestamp = status['time']
                        break

                # All datasets are VALID and workflow was 'completed'
                if not not_valid_datasets and completed_timestamp:
                    self.update_status(relval, 'done', completed_timestamp)
                    results.append(relval)
                    continue

                # Get time when workflow became archived
                archived_timestamp = None
                for status in status_history:
                    if status['status'] in archived_status:
                        archived_timestamp = status['time']
                        break

                # Workflow was archived for more than the threshold
                if archived_timestamp and archived_timestamp <= archived_threshold:
                    self.update_status(relval, 'archived', archived_timestamp)
                    results.append(relval)
                    continue

                if not_valid_datasets:
                    datatiers = [ds.split('/')[-1] for ds in not_valid_datasets]
                    raise Exception(f'Could not move {prepid} to "done" because '
                                    f'{len(not_valid_datasets)} datasets are not VALID: '
                                    f'{", ".join(datatiers)}')

                last_workflow_name = last_workflow['name']
                if not completed_timestamp:
                    raise Exception(f'Could not move {prepid} to "done" because '
                                    f'{last_workflow} is not yet "completed"')

                raise Exception(f'Could not move {prepid} to "archived" because '
                                f'{last_workflow_name} is not archived long enough')

        return results

    def move_relval_back_to_new(self, relval):
        """
        Try to move RelVal back to new
        """
        for step in relval.get('steps'):
            step.set('resolved_globaltag', '')

        self.update_status(relval, 'new')
        return relval

    def move_relval_back_to_approved(self, relval):
        """
        Try to move RelVal back to approved
        """
        relval = self.update_workflows(relval)
        active_workflows = self.pick_active_workflows(relval)
        # refresh_workflows_in_stats([x['name'] for x in active_workflows])
        # Take active workflows again in case any of them changed during Stats refresh
        # active_workflows = self.pick_active_workflows(relval)
        if active_workflows:
            self.reject_workflows(active_workflows)
            # Refresh after rejecting
            # refresh_workflows_in_stats([x['name'] for x in active_workflows])
            relval = self.update_workflows(relval)

        for step in relval.get('steps'):
            step.set('config_id', '')

        relval.set('campaign_timestamp', 0)
        relval.set('output_datasets', [])
        self.update_status(relval, 'approved')
        return relval

    def pick_workflows(self, all_workflows, output_datasets):
        """
        Pick, process and sort workflows from computing based on output datasets
        """
        new_workflows = []
        self.logger.info('Picking workflows %s for datasets %s',
                         [x['RequestName'] for x in all_workflows.values()],
                         output_datasets)
        for _, workflow in all_workflows.items():
            new_workflow = {'name': workflow['RequestName'],
                            'type': workflow['RequestType'],
                            # 'total_events': workflow['TotalEvents'],
                            'output_datasets': [],
                            'status_history': []}
            for output_dataset in output_datasets:
                for history_entry in reversed(workflow.get('EventNumberHistory', [])):
                    if output_dataset in history_entry['Datasets']:
                        dataset_dict = history_entry['Datasets'][output_dataset]
                        new_workflow['output_datasets'].append({'name': output_dataset,
                                                                'type': dataset_dict['Type'],
                                                                'events': dataset_dict['Events']})
                        break

            for request_transition in workflow.get('RequestTransition', []):
                new_workflow['status_history'].append({'time': request_transition['UpdateTime'],
                                                       'status': request_transition['Status']})

            new_workflows.append(new_workflow)

        new_workflows = sorted(new_workflows, key=lambda w: '_'.join(w['name'].split('_')[-3:]))
        self.logger.info('Picked workflows:\n%s',
                         ', '.join([w['name'] for w in new_workflows]))
        return new_workflows

    def pick_active_workflows(self, relval):
        """
        Filter out workflows that are rejected, aborted or failed
        """
        prepid = relval.get_prepid()
        workflows = relval.get('workflows')
        active_workflows = []
        for workflow in workflows:
            status_history = set(x['status'] for x in workflow.get('status_history', []))
            if not DEAD_WORKFLOW_STATUS & status_history:
                active_workflows.append(workflow)

        self.logger.info('Active workflows of %s are %s',
                         prepid,
                         ', '.join([x['name'] for x in active_workflows]))
        return active_workflows

    def reject_workflows(self, workflows):
        """
        Reject or abort list of workflows in ReqMgr2
        """
        workflow_status_pairs = []
        for workflow in workflows:
            workflow_name = workflow['name']
            status_history = workflow.get('status_history')
            if not status_history:
                self.logger.error('%s has no status history', workflow_name)
                status_history = [{'status': '<unknown>'}]

            last_workflow_status = status_history[-1]['status']
            workflow_status_pairs.append((workflow_name, last_workflow_status))

        cmsweb_reject_workflows(workflow_status_pairs)

    def update_workflows(self, relval):
        """
        Update computing workflows from Reqmgr2
        """
        prepid = relval.get_prepid()
        relval_db = Database('relvals')
        with self.locker.get_lock(prepid):
            relval = self.get(prepid)
            workflow_names = {w['name'] for w in relval.get('workflows')}
            stats_workflows = get_workflows_from_reqmgr2_for_prepid(prepid)
            workflow_names -= {w['RequestName'] for w in stats_workflows}
            self.logger.info('%s workflows that are not in stats: %s',
                             len(workflow_names),
                             workflow_names)
            stats_workflows += get_workflows_from_reqmgr2(list(workflow_names))
            all_workflows = {}
            for workflow in stats_workflows:
                if not workflow or not workflow.get('RequestName'):
                    raise Exception('Could not find workflow in Reqmgr2')

                name = workflow.get('RequestName')
                all_workflows[name] = workflow
                self.logger.info('Found workflow %s', name)

            output_datasets = self.get_output_datasets(relval, all_workflows)
            workflows = self.pick_workflows(all_workflows, output_datasets)
            relval.set('output_datasets', output_datasets)
            relval.set('workflows', workflows)
            relval_db.save(relval.get_json())

        return relval

    def get_output_datasets(self, relval, all_workflows):
        """
        Return a list of sorted output datasets for RelVal from given workflows
        """
        output_datatiers = []
        prepid = relval.get_prepid()
        for step in relval.get('steps'):
            output_datatiers.extend(step.get('driver')['datatier'])

        output_datatiers_set = set(output_datatiers)
        self.logger.info('%s output datatiers are: %s', prepid, ', '.join(output_datatiers))
        output_datasets_tree = {k: {} for k in output_datatiers}
        for workflow_name, workflow in all_workflows.items():
            if workflow.get('RequestType', '').lower() == 'resubmission':
                continue

            status_history = set(x['Status'] for x in workflow.get('RequestTransition', []))
            if DEAD_WORKFLOW_STATUS & status_history:
                self.logger.debug('Ignoring %s', workflow_name)
                continue

            for output_dataset in workflow.get('OutputDatasets', []):
                output_dataset_parts = [x.strip() for x in output_dataset.split('/')]
                output_dataset_datatier = output_dataset_parts[-1]
                output_dataset_no_datatier = '/'.join(output_dataset_parts[:-1])
                output_dataset_no_version = '-'.join(output_dataset_no_datatier.split('-')[:-1])
                if output_dataset_datatier in output_datatiers_set:
                    datatier_tree = output_datasets_tree[output_dataset_datatier]
                    if output_dataset_no_version not in datatier_tree:
                        datatier_tree[output_dataset_no_version] = []

                    datatier_tree[output_dataset_no_version].append(output_dataset)

        self.logger.debug('Output datasets tree:\n%s',
                          json.dumps(output_datasets_tree,
                                     indent=2,
                                     sort_keys=True))
        output_datasets = []
        for _, datasets_without_versions in output_datasets_tree.items():
            for _, datasets in datasets_without_versions.items():
                if datasets:
                    output_datasets.append(sorted(datasets)[-1])

        def tier_level_comparator(dataset):
            dataset_tier = dataset.split('/')[-1:][0]
            if dataset_tier in output_datatiers_set:
                return output_datatiers.index(dataset_tier)

            return -1

        output_datasets = sorted(output_datasets, key=tier_level_comparator)
        self.logger.debug('Output datasets:\n%s',
                          json.dumps(output_datasets,
                                     indent=2,
                                     sort_keys=True))
        return output_datasets

    def get_new_dataset_version(self, dataset, run):
        """Get new version for the dataset to avoid overwrite issue"""
        version = int(dataset.split("/")[-2].split("-")[-1].strip('v'))
        cmssw_version = dataset.split('/')[2].split('-')[0]
        stript_cmssw = '_'.join(cmssw_version.split('_')[:3]+['x/'])
        dataset_name = dataset.replace('/', '__')

        while True:
            file = f'DQM_V0001_R000{run[0]}{dataset_name}.root'
            urlpart = stript_cmssw + file
            data_exists = check_if_dataset_exists(urlpart)
            if data_exists:
                dataset_name = dataset_name.replace(f'-v{version}__', f'-v{version+1}__')
                version = version + 1
            else:
                return version

    def compare_dqm_datasets(self, relvalT, relvalR):
        """Compare DQM dataset pair and save info to database"""
        def get_dqm_pair(relvalT, relvalR):
            """Returns DQM dataset pair for the relvals"""
            # Get run numbers
            in_dataT = relvalT.get('steps')[0].get('input')
            in_dataR = relvalR.get('steps')[0].get('input')
            runT = in_dataT.get('lumisection') or in_dataT.get('run')
            runR = in_dataR.get('lumisection') or in_dataR.get('run')
            runT = list(runT.keys()) if isinstance(runT, dict) else runT
            runR = list(runR.keys()) if isinstance(runR, dict) else runR

            dqm_pair = {}
            dqm_pair['tar_run'] = runT
            dqm_pair['ref_run'] = runR
            for dataset in [i for i in relvalT.get('output_datasets') if 'DQMIO' in i]:
                dqm_pair['tar_dataset'] = dataset
            for dataset in [i for i in relvalR.get('output_datasets') if 'DQMIO' in i]:
                dqm_pair['ref_dataset'] = dataset
            return dqm_pair
        dqm_pair = get_dqm_pair(relvalT, relvalR)

        results = []
        lock_key = '+'.join([relvalR.get_prepid(), relvalT.get_prepid()])
        with self.locker.get_nonblocking_lock(lock_key):
            relval_db = Database('relvals')
            target_pair = []
            for dqmtype, relval in zip(['tar', 'ref'], [relvalT, relvalR]):
                a, b = (dqmtype, 'ref') if dqmtype == 'tar' else (dqmtype, 'tar')
                batch_name = relval.get('batch_name')
                cmssw_release = relval.get('cmssw_release')
                locker_key = f'compare-dqm-plots-bin-by-bin-{cmssw_release}__{batch_name}'

                with self.locker.get_lock(locker_key):
                    dqm = relval.get_json().get('dqm_comparison')
                    if not isinstance(dqm, list): dqm = []
                    for item in dqm:
                        # Check if pair is already compared
                        source = bool(item['source'] == dqm_pair[f'{a}_dataset'])
                        compared_with = bool(item['compared_with'] == dqm_pair[f'{b}_dataset'])
                        if source and compared_with:
                            self.logger.error('This pair is already compared. Not repeating the task. %s and %s', 
                                        item['source'], 
                                        item['compared_with'])
                            return []

                    old_ver = dqm_pair[f'{a}_dataset'].split("/")[-2].split("-")[-1].strip('v')
                    version = self.get_new_dataset_version(dqm_pair[f'{a}_dataset'], dqm_pair[f'{a}_run'])
                    target_data = dqm_pair[f'{a}_dataset'].replace(f'-v{old_ver}/', f'-v{version}/').replace('/', '__')

                    old_ver = dqm_pair[f'{b}_dataset'].split("/")[-2].split("-")[-1].strip('v')
                    version = self.get_new_dataset_version(dqm_pair[f'{b}_dataset'], dqm_pair[f'{b}_run'])
                    reference_data = dqm_pair[f'{b}_dataset'].replace(f'-v{old_ver}/', f'-v{version}/')

                    target_pair.append(target_data)

                    info = {'source': dqm_pair[f'{a}_dataset'],
                            'compared_with': dqm_pair[f'{b}_dataset'],
                            'target': target_data.replace('__', '/'),
                            'reference': reference_data,
                            'status': 'comparing',
                            'run_number': dqm_pair['tar_run'],
                            'tar_run': dqm_pair[f'{a}_run'],
                            'ref_run': dqm_pair[f'{b}_run']
                            }
                    relval.set('dqm_comparison', dqm+[info])
                    relval_db.save(relval.get_json())
            DQMRequestSubmitter().add(relvalT, relvalR, dqm_pair, target_pair)
        return results
