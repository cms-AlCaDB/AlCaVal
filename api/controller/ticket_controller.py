"""
Module that contains TicketController class
"""
import json
import os
import time, datetime
from copy import deepcopy
from database.database import Database
from core_lib.controller.controller_base import ControllerBase
from core_lib.utils.ssh_executor import SSHExecutor
from core_lib.utils.common_utils import (clean_split,
                                        cmssw_setup,
                                        get_scram_arch,
                                        dbs_datasetlist,
                                        run_commands_in_cmsenv)
from core_lib.utils.global_config import Config
from ..model.ticket import Ticket
from ..model.relval import RelVal
from ..model.relval_step import RelValStep
from ..controller.relval_controller import RelValController


class TicketController(ControllerBase):
    """
    Ticket controller performs all actions with tickets
    """

    def __init__(self):
        ControllerBase.__init__(self)
        self.database_name = 'tickets'
        self.model_class = Ticket

    def create(self, json_data):
        # Clean up the input
        cmssw_release = json_data.get('cmssw_release')
        batch_name = json_data.get('batch_name')
        prepid_part = f'{cmssw_release}__{batch_name}'
        ticket_db = Database('tickets')
        json_data['prepid'] = f'{prepid_part}-00000'
        with self.locker.get_lock(f'generate-ticket-prepid-{prepid_part}'):
            # Get a new serial number
            serial_number = self.get_highest_serial_number(ticket_db,
                                                           f'{prepid_part}-*')
            serial_number += 1
            # Form a new temporary prepid
            prepid = f'{prepid_part}-{serial_number:05d}'
            json_data['prepid'] = prepid
            ticket = super().create(json_data)

        return ticket

    def get_editing_info(self, obj):
        editing_info = super().get_editing_info(obj)
        prepid = obj.get_prepid()
        status = obj.get('status')
        creating_new = not bool(prepid)
        not_done = status != 'done'
        editing_info['prepid'] = False
        editing_info['batch_name'] = creating_new
        editing_info['cmssw_release'] = creating_new
        editing_info['jira_ticket'] = True
        editing_info['command'] = not_done
        editing_info['command_steps'] = not_done
        editing_info['cpu_cores'] = not_done
        editing_info['gpu'] = not_done
        editing_info['gpu_steps'] = not_done
        editing_info['label'] = not_done
        editing_info['matrix'] = not_done
        editing_info['memory'] = not_done
        editing_info['notes'] = True
        editing_info['n_streams'] = not_done
        editing_info['recycle_gs'] = not_done
        editing_info['recycle_input_of'] = not_done
        editing_info['rewrite_gt_string'] = not_done
        editing_info['sample_tag'] = not_done
        editing_info['title'] = True
        editing_info['cms_talk_link'] = True
        editing_info['hlt_gt'] = not_done
        editing_info['prompt_gt'] = not_done
        editing_info['express_gt'] = not_done
        editing_info['common_prompt_gt'] = not_done
        editing_info['hlt_gt_ref'] = not_done
        editing_info['prompt_gt_ref'] = not_done
        editing_info['express_gt_ref'] = not_done
        editing_info['attached_wfs'] = not_done
        editing_info['scram_arch'] = not_done
        editing_info['workflow_ids'] = not_done

        return editing_info

    def check_for_delete(self, obj):
        created_relvals = obj.get('created_relvals')
        prepid = obj.get('prepid')
        if created_relvals:
            raise Exception(f'It is not allowed to delete tickets that have relvals created. '
                            f'{prepid} has {len(created_relvals)} relvals')

        return True

    def rewrite_gt_string_if_needed(self, workflow_id, step, gt_rewrite):
        """
        Perform base dataset rewrite if needed:
          - rewrite middle part of input dataset name for input steps
          - rewrite middle part of --pileup_input for driver steps
        """
        if not gt_rewrite:
            return

        input_dict = step['input']
        driver_dict = step['driver']
        if input_dict.get('dataset'):
            # Input dataset step
            input_dataset = input_dict['dataset']
            self.logger.info('Will replace %s middle part with %s', input_dataset, gt_rewrite)
            input_dataset_split = input_dataset.split('/')
            input_dataset_split[2] = gt_rewrite
            input_dataset = '/'.join(input_dataset_split)
            dataset_list = dbs_datasetlist(input_dataset)
            if not dataset_list:
                raise Exception(f'Could not find {input_dataset} input dataset for {workflow_id} '
                                f'after applying {gt_rewrite} GT rewrite')

            input_dataset = sorted([x['dataset'] for x in dataset_list])[-1]
            input_dict['dataset'] = input_dataset
        elif driver_dict.get('pileup_input'):
            # Driver step
            pileup_input = driver_dict['pileup_input']
            # Removing PU_ from the pileup input dataset because it is already
            # clear that PU dataset is PU without PU_
            gt_rewrite = gt_rewrite.replace('-PU_', '-')
            # Due to removal of PU_, the version might be different, so fetch
            # the newest one
            gt_rewrite = gt_rewrite.split('-')
            if gt_rewrite[-1].startswith('v'):
                gt_rewrite[-1] = 'v*'

            gt_rewrite = '-'.join(gt_rewrite)
            self.logger.info('Will replace %s middle part with %s', pileup_input, gt_rewrite)
            pileup_input_split = pileup_input.split('/')
            pileup_input_split[2] = gt_rewrite
            pileup_input = '/'.join(pileup_input_split)
            pileup_prefix = pileup_input[:pileup_input.index('/')]
            dataset_list = dbs_datasetlist(pileup_input)
            if not dataset_list:
                raise Exception(f'Could not find {pileup_input} PU dataset for {workflow_id}')

            pileup_input = sorted([x['dataset'] for x in dataset_list])[-1]
            driver_dict['pileup_input'] = f'{pileup_prefix}{pileup_input}'

    def recycle_input_with_gt_rewrite(self, relvals, gt_rewrite, recycle_input_of):
        """
        Try to recycle input (based on --step) for certain steps by replacing
        steps by an input dataset when Rewrite GT string is provided
        """
        self.logger.debug('Recycling with GT string input for %s', recycle_input_of)
        for relval in relvals:
            relval_steps = relval.get('steps')
            recycled_step = None
            recycle_index = 0
            for index, step in enumerate(relval_steps):
                if step.has_step(recycle_input_of):
                    recycled_step = relval_steps[index - 1]
                    recycle_index = index
                    break
            else:
                continue

            relval_name = relval.get_name()
            datatier = recycled_step.get('driver')['datatier'][-1]
            dataset = f'/RelVal{relval_name}/{gt_rewrite}/{datatier}'
            self.logger.debug('Recycled input dataset %s', dataset)
            input_step_json = recycled_step.get_json()
            input_step_json['driver'] = {}
            input_step_json['input'] = {'dataset': dataset,
                                        'lumisection': {},
                                        'run': [],
                                        'label': ''}
            input_step = RelValStep(input_step_json, relval, False)
            relval.set('steps', [input_step] + relval_steps[recycle_index:])

    def recycle_input(self, relvals, relval_controller, recycle_input_of):
        """
        Try to recycle input (based on --step) for certain steps by replacing
        steps by an input dataset when there is no Rewrite GT string available
        """
        self.logger.debug('Automagic recycling input for %s', recycle_input_of)
        conditions_tree = {}
        selected_relvals = []
        for relval in relvals:
            relval_steps = relval.get('steps')
            recycled_index = 0
            for index, step in enumerate(relval_steps):
                if step.has_step(recycle_input_of):
                    recycled_index = index - 1
                    break
            else:
                continue

            recycled_step = relval_steps[recycled_index]
            selected_relvals.append((relval, recycled_step, recycled_index))
            conditions = recycled_step.get('driver')['conditions']
            if not conditions.startswith('auto:'):
                # Collect only auto: ... conditions
                continue

            cmssw = recycled_step.get_release()
            scram = recycled_step.get_scram_arch()
            conditions_tree.setdefault(cmssw, {}).setdefault(scram, {})[conditions] = None

        # Resolve auto:conditions to actual globaltags
        self.logger.debug('Conditions:\n%s', json.dumps(conditions_tree, indent=2))
        relval_controller.resolve_auto_conditions(conditions_tree)
        self.logger.debug('Resolved conditions:\n%s', json.dumps(conditions_tree, indent=2))
        for relval, recycled_step, recycled_index in selected_relvals:
            relval_steps = relval.get('steps')
            conditions = recycled_step.get('driver')['conditions']
            cmssw = recycled_step.get_release()
            if conditions.startswith('auto:'):
                scram = recycled_step.get_scram_arch()
                conditions = conditions_tree[cmssw][scram][conditions]

            recycled_step.set('resolved_globaltag', conditions)
            processing_string = relval.get_processing_string(recycled_index)
            recycled_step.set('resolved_globaltag', '')
            relval_name = relval.get_name()
            datatier = recycled_step.get('driver')['datatier'][-1]
            dataset = f'/RelVal{relval_name}/{cmssw}-{processing_string}-v*/{datatier}'
            relval_id = relval.get('workflow_id')
            self.logger.debug('Recycled input dataset template %s for %s', dataset, relval_id)
            dataset_list = dbs_datasetlist(dataset)
            if not dataset_list:
                raise Exception(f'Could not find a recyclable input for {relval_name} '
                                f'({relval_id}), query: {dataset}, step: {recycle_input_of}')

            dataset = sorted([x['dataset'] for x in dataset_list])[-1]
            input_step_json = recycled_step.get_json()
            input_step_json['driver'] = {}
            input_step_json['input'] = {'dataset': dataset,
                                        'lumisection': {},
                                        'run': [],
                                        'label': ''}
            input_step_json['name'] += '_Recycled'
            input_step = RelValStep(input_step_json, relval, False)
            relval.set('steps', [input_step] + relval_steps[(recycled_index + 1):])
            self.logger.debug(relval)

    def make_relval_step(self, step_dict):
        """
        Remove, split or move arguments in step dictionary
        returned from run_the_matrix_alca.py
        """
        # Deal with input file part
        input_dict = step_dict.get('input', {})
        input_dict.pop('events', None)

        # Deal with driver part
        arguments = step_dict.get('arguments', {})
        # Remove unneeded arguments
        for to_pop in ('--filein', '--fileout', '--lumiToProcess'):
            arguments.pop(to_pop, None)

        # Split comma separated items into lists
        for to_split in ('--step', '--eventcontent', '--datatier'):
            arguments[to_split] = clean_split(arguments.get(to_split, ''))

        # Put all arguments that are not in schema to extra field
        driver_schema = RelValStep.schema()['driver']
        driver_keys = {f'--{key}' for key in driver_schema.keys()}
        extra = ''
        for key, value in arguments.items():
            if key == 'fragment_name':
                continue

            if key not in driver_keys:
                if isinstance(value, bool):
                    if value:
                        extra += f' {key}'
                elif isinstance(value, list):
                    if value:
                        extra += f' {key} {",".join(value)}'
                else:
                    if value:
                        extra += f' {key} {value}'

        arguments['extra'] = extra.strip()
        arguments = {k.lstrip('-'): v for k, v in arguments.items()}
        # Create a step
        name = step_dict['name']
        # Delete INPUT from step name
        if name.endswith('INPUT'):
            name = name[:-5]

        new_step = {'name': name,
                    'lumis_per_job': step_dict.get('lumis_per_job', ''),
                    'events_per_lumi': step_dict.get('events_per_lumi', ''),
                    'driver': arguments,
                    'input': input_dict}

        self.logger.debug('Step dict: %s', json.dumps(new_step, indent=2))
        return new_step

    def generate_workflows(self, ticket, ssh_executor):
        """
        Remotely run workflow info extraction from CMSSW and return all workflows
        """
        ticket_prepid = ticket.get_prepid()
        remote_directory = Config.get('remote_path').rstrip('/')
        if ticket.get('recycle_gs') and not ticket.get('recycle_input_of'):
            recycle_gs_flag = '-r '
        else:
            recycle_gs_flag = ''

        cmssw_release = ticket.get('cmssw_release')
        scram_arch = ticket.get('scram_arch')
        scram_arch = scram_arch if scram_arch else get_scram_arch(cmssw_release)
        if not scram_arch:
            raise Exception(f'Could not find SCRAM arch of {cmssw_release}')

        matrix = ticket.get('matrix')
        additional_command = ticket.get('command').strip()
        command_steps = ticket.get('command_steps')
        if additional_command:
            additional_command = additional_command.replace('"', '\\"')
            additional_command = f'-c="{additional_command}"'
            if command_steps:
                command_steps = ','.join(command_steps)
                additional_command += f' -cs={command_steps}'
        else:
            additional_command = ''

        workflow_ids = ','.join([str(x) for x in ticket.get('workflow_ids')])
        self.logger.info('Creating RelVals %s for %s', workflow_ids, ticket_prepid)
        # Prepare remote directory with run_the_matrix_alca.py
        command = [f'mkdir -p {remote_directory}']
        _, err, code = ssh_executor.execute_command(command)
        if code != 0:
            raise Exception(f'Error code {code} preparing workspace: {err}')

        ssh_executor.upload_file('api/utils/run_the_matrix_alca.py',
                                 f'{remote_directory}/run_the_matrix_alca.py')
        # Defined a name for output file
        file_name = f'{ticket_prepid}_{int(time.time())}.json'

        # Execute run_the_matrix_alca.py
        matrix_command = run_commands_in_cmsenv([f'cd {remote_directory}',
                                                 '$PYTHON_INT run_the_matrix_alca.py '
                                                 f'-l={workflow_ids} '
                                                 f'-w={matrix} '
                                                 f'-o={file_name} '
                                                 f'{additional_command} '
                                                 f'{recycle_gs_flag}'],
                                                cmssw_release,
                                                scram_arch)
        _, err, code = ssh_executor.execute_command(matrix_command)
        if code != 0:
            raise Exception(f'Error code {code} creating RelVals. stdout: {out}, stderr: {err}')

        # Download generated json
        ssh_executor.download_file(f'{remote_directory}/{file_name}',
                                   f'/tmp/{file_name}')

        # Cleanup remote directory by removing all ticket jsons
        ssh_executor.execute_command(f'rm -rf {remote_directory}/{ticket_prepid}_*.json')
        with open(f'/tmp/{file_name}', 'r') as workflows_file:
            workflows = json.load(workflows_file)

        os.remove(f'/tmp/{file_name}')
        return workflows

    def create_relval_from_workflow(self, ticket, workflow_id, workflow_dict, cond_tag=''):
        """
        Create a RelVal from given workflow
        """
        workflow_dict = deepcopy(workflow_dict)
        cmssw_release = ticket.get('cmssw_release')
        jira_ticket = ticket.get('jira_ticket')
        scram_arch = ticket.get('scram_arch')
        n_streams = ticket.get('n_streams')
        gpu_dict = ticket.get('gpu')
        gpu_steps = ticket.get('gpu_steps')
        rewrite_gt_string = ticket.get('rewrite_gt_string')
        relval_json = {'prepid': 'TempRelValObject-00000',
                       'batch_name': ticket.get('batch_name'),
                       'cmssw_release': cmssw_release,
                       'jira_ticket': jira_ticket,
                       'cpu_cores': ticket.get('cpu_cores'),
                       'label': ticket.get('label'),
                       'memory': ticket.get('memory'),
                       'matrix': ticket.get('matrix'),
                       'sample_tag': ticket.get('sample_tag'),
                       'scram_arch': scram_arch,
                       'steps': [],
                       'workflow_id': workflow_id,
                       'workflow_name': workflow_dict['workflow_name']}

        step_length = len(workflow_dict['steps'])
        for step_index, step_dict in enumerate(workflow_dict['steps']):
            new_step = self.make_relval_step(step_dict)
            new_step['cmssw_release'] = ''
            new_step['scram_arch'] = ''
            if n_streams > 0:
                new_step['driver']['nStreams'] = n_streams

            step_steps = [x.split(':')[0] for x in new_step['driver']['step']]
            if gpu_steps and (set(gpu_steps) & set(step_steps)):
                new_step['gpu'] = deepcopy(gpu_dict)

            if 'HLT' in cond_tag and step_index == 1:
                new_step['driver']['conditions'] = ticket.get('hlt_gt{}'.format('_ref' if 'Ref' in cond_tag else ''))
            elif 'HLT' in cond_tag and step_index != 0:
                new_step['driver']['conditions'] = ticket.get('common_prompt_gt')
            if 'Prompt' in cond_tag and step_index != 0:
                new_step['driver']['conditions'] = ticket.get('prompt_gt{}'.format('_ref' if 'Ref' in cond_tag else ''))
            if 'Express' in cond_tag and step_index != 0:
                new_step['driver']['conditions'] = ticket.get('express_gt{}'.format('_ref' if 'Ref' in cond_tag else ''))

            # Keep only DQMIO output
            if step_index >= step_length-2:
                new_step['keep_output'] = True
            else:
                new_step['keep_output'] = False

            self.rewrite_gt_string_if_needed(workflow_id, new_step, rewrite_gt_string)
            relval_json['steps'].append(new_step)

        return RelVal(relval_json, False)

    def create_relval_for_alca(self, ticket, workflows):
        attached_wfs = ticket.get('attached_wfs')
        alca_wfs = []
        for k, v in attached_wfs.items(): alca_wfs = alca_wfs + v
        alca_wfs = set(alca_wfs)
        relvals = []
        relval_tags = []
        for workflow_id, workflow_dict in workflows.items():
            if not float(workflow_id) in alca_wfs:
                relvals.append(self.create_relval_from_workflow(ticket,
                                                        workflow_id,
                                                        workflow_dict))
                relval_tags.append(('', workflow_id))
            for condName in ['HLT', 'Prompt', 'Express']:
                condKeys = [('New', condName.lower()+'_gt'), ('Ref', condName.lower()+'_gt_ref')]
                WFnames = [condName+wtype for wtype, wf in condKeys if ticket.get(wf)]
                if float(workflow_id) in attached_wfs[condName]:
                    for WFname in WFnames:
                        relvals.append(
                            self.create_relval_from_workflow(ticket,
                                                    workflow_id,
                                                    workflow_dict, 
                                                    WFname)
                            )
                        relval_tags.append((WFname, workflow_id))
        return (relvals, relval_tags)

    def create_relvals_for_ticket(self, ticket):
        """
        Create RelVals from given ticket. Return list of relval prepids
        """
        ticket_db = Database('tickets')
        ticket_prepid = ticket.get_prepid()
        ssh_executor = SSHExecutor('lxplus.cern.ch', Config.get('credentials_file'))
        relval_controller = RelValController()
        created_relvals = []
        with self.locker.get_lock(ticket_prepid):
            ticket = self.get(ticket_prepid)
            rewrite_gt_string = ticket.get('rewrite_gt_string')
            recycle_input_of = ticket.get('recycle_input_of')
            try:
                workflows = self.generate_workflows(ticket, ssh_executor)
                # Iterate through workflows and create RelVal objects
                relvals, relval_tags = self.create_relval_for_alca(ticket, workflows)

                # Handle recycling if needed
                if recycle_input_of:
                    if rewrite_gt_string:
                        self.recycle_input_with_gt_rewrite(relvals,
                                                           rewrite_gt_string,
                                                           recycle_input_of)
                    else:
                        self.recycle_input(relvals,
                                           relval_controller,
                                           recycle_input_of)

                for relval, relval_tag in zip(relvals, relval_tags):
                    relval = relval_controller.create(relval.get_json(), condition_name=relval_tag[0])
                    created_relvals.append(relval)
                    self.logger.info('Created %s', relval.get_prepid())

                created_relval_prepids = [r.get('prepid') for r in created_relvals]
                ticket.set('created_relvals', created_relval_prepids)
                ticket.set('status', 'done')
                ticket.add_history('created_relvals', created_relval_prepids, None)
                ticket_db.save(ticket.get_json())
            except Exception as ex:
                self.logger.error('Error creating RelVal from ticket: %s', ex)
                # Delete created relvals if there was an Exception
                for created_relval in reversed(created_relvals):
                    relval_controller.delete({'prepid': created_relval.get('prepid')})

                # And reraise the exception
                raise ex
            finally:
                # Close all SSH connections
                ssh_executor.close_connections()

        return [r.get('prepid') for r in created_relvals]

    def get_workflows_list(self, ticket):
        """
        Get a list of workflow names of created RelVals for RelMon Service
        """
        relvals_db = Database('relvals')
        created_relvals = ticket.get('created_relvals')
        created_relvals_prepids = ','.join(created_relvals)
        query = f'prepid={created_relvals_prepids}'
        results, _ = relvals_db.query_with_total_rows(query, limit=len(created_relvals))
        workflows = []
        for relval in results:
            if not relval['workflows']:
                continue

            workflows.append(relval['workflows'][-1]['name'])

        if not workflows:
            workflows.append('# No workflow names')

        self.logger.debug('Workflow names for %s:\n%s', ticket.get_prepid(), '\n'.join(workflows))
        return workflows

    def get_run_the_matrix(self, ticket):
        """
        Get a runTheMatrix command for the ticket using ticket's attributes
        """
        command = 'runTheMatrix.py'
        batch_name = ticket.get('batch_name')
        matrix = ticket.get('matrix')
        label = ticket.get('label')
        cpu_cores = ticket.get('cpu_cores')
        memory = ticket.get('memory')
        custom_command = ticket.get('command')
        workflows = ','.join([str(x) for x in ticket.get('workflow_ids')])
        adjusted_memory = max(1000, memory - ((cpu_cores - 1) * 1500))
        recycle_gs = ticket.get('recycle_gs')
        # Build the command
        command += f' -w "{matrix}"'
        command += f' -b "{batch_name}"'
        if label:
            command += f' --label "{label}"'

        command += f' -t {cpu_cores}'
        command += f' -m {adjusted_memory}'
        command += f' -l {workflows}'
        if recycle_gs:
            command += ' -i all'

        if custom_command:
            command += f' --command="{custom_command}"'

        command += ' --noCaf --wm force'
        self.logger.debug('runTheMatrix.py for %s:\n%s', ticket.get_prepid(), command)
        return command

    def get_input_info_for_jira(self, ticket):
        """
        Getting summary, description for jira ticket
        """

        relval_controller = RelValController()
        created_relvals = ticket.get('created_relvals')
        result = {}
        for relval_prepid in created_relvals:
            relval = relval_controller.get(relval_prepid)
            relval = relval.get_json()

            runs = set(relval.get('steps')[0]['input']['lumisection'].keys())
            if not len(runs):
                runs = set(relval.get('steps')[0]['input']['run'].split(','))
            if result.get('run_number'):
                result['run_number'] = result['run_number'] | runs
            else:
                result['run_number'] = runs

            dataset = relval.get('steps')[0]['input']['dataset']
            if result.get('datasets'):
                result.get('datasets').add(dataset)
            else:
                result['datasets'] = set([dataset])

            gtag = relval.get('steps')[1]['driver']['conditions']
            if result.get('global_tags'):
                result['global_tags'].add(gtag)
            else:
                result['global_tags'] = set([gtag])

            cmssw = relval.get('cmssw_release')
            cmssw = set(result.get('cmssw_release')) if result.get('cmssw_release') else set() | {cmssw}
            result['cmssw_release'] = cmssw

        # Getting summary
        hlt = 'HLT' if (ticket.get('hlt_gt') or ticket.get('hlt_gt_ref')) else None
        prompt = 'Prompt' if (ticket.get('prompt_gt') or ticket.get('prompt_gt_ref')) else None
        express = 'Express' if (ticket.get('express_gt') or ticket.get('express_gt_ref')) else None
        conditions = list(filter(None, [hlt, prompt, express]))
        summary_tag = '/'.join(conditions)
        summary_title = ticket.get('title')

        date = datetime.date.today()
        year, week_num, day_of_week = date.isocalendar()
        summary_date = f'(Week {week_num}, {year})'
        summary = f'[{summary_tag}] {summary_title} {summary_date}'
        result['summary'] = summary

        cmsoms = '[{run}|https://cmsoms.cern.ch/cms/runs/report?cms_run={run}&cms_run_sequence=GLOBAL-RUN]'
        run_numbers = [cmsoms.format(run=run) for run in result.get('run_number')]

        cmsswLink = '[{cmssw}|https://github.com/cms-sw/cmssw/releases/tag/{cmssw}]'
        cmssw = [cmsswLink.format(cmssw=cmssw) for cmssw in result.get('cmssw_release')]

        input_info = " * Run numbers: %s\n"%(', '.join(run_numbers))
        input_info += " * CMSSW release: %s\n"%(', '.join(cmssw))
        input_info += " * Datasets:\n"
        for dataset in result.get('datasets'):
            input_info += f" ** [{dataset}|https://cmsweb.cern.ch/das/request?input={dataset}]\n"

        # Getting description
        gt_list = ''
        tag_link = 'https://cms-conddb.cern.ch/cmsDbBrowser/list/Prod/gts/{}'
        diff = 'https://cms-conddb.cern.ch/cmsDbBrowser/diff/Prod/gts/{target}/{ref}'
        for cond in conditions:
            gt = ticket.get(cond.lower()+'_gt')
            if gt:
                gt_list += f' * Target {cond} GT: [{gt}|{tag_link.format(gt)}]\n'
            gt_ref = ticket.get(cond.lower()+'_gt_ref')
            if gt_ref:
                gt_list += f' * Reference {cond} GT: [{gt_ref}|{tag_link.format(gt_ref)}]\n'
            if cond == 'HLT':
                common_gt = ticket.get('common_prompt_gt')
                gt_list += f' * Common Prompt GT: [{common_gt}|{tag_link.format(common_gt)}]\n'
            if gt and gt_ref:
                differ = diff.format(target=gt, ref=gt_ref)
                gt_list += f' * Difference: [{cond} target vs reference|{differ}]\n'
            gt_list += '\n'
        description = f"""Dear Colleagues, 
We are going to perform {summary_title}.
Request email for this validation is [0].
Details of the workflow:
{gt_list}{input_info}
Details of the submission is available at [1].
Once the workflows are ready, we will ask the validators to report the outcome of the checks at this Jira ticket.

Best regards,
AlCa/DB Team

[0] {ticket.get('cms_talk_link')}
[1] {Config.get('service_url')}/relvals?ticket={ticket.get('prepid')}
"""
        result['description'] = description
        for key, value in result.items():
            if isinstance(value, set):
                result[key] = list(value)
        return result