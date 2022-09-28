"""
Module that contains RelValStep class
"""
import weakref
import json
from copy import deepcopy
from ..model.model_base import ModelBase
from core_lib.utils.common_utils import get_scram_arch


class RelValStep(ModelBase):
    """
    RelVal is one step of RelVal - either a call to DAS for list of input files
    or a cmsDriver command
    """

    _ModelBase__schema = {
        # Step name
        'name': '',
        # CMSSW version of this step
        'cmssw_release': '',
        # Hash of configuration file uploaded to ReqMgr2
        'config_id': '',
        # Size Per Event for a step
        'size_per_event': 3000,
        # Time per Event for a step
        'time_per_event': 20,
        # cmsDriver arguments
        'driver': {
            'beamspot': '',
            'conditions': '',
            'customise': '',
            'customise_commands': '',
            'data': False,
            'datatier': [],
            'era': '',
            'eventcontent': [],
            'extra': '',
            'fast': False,
            'filetype': '',
            'geometry': '',
            'hltProcess': '',
            'mc': False,
            'number': '10',
            'nStreams': '',
            'pileup': '',
            'pileup_input': '',
            'process': '',
            'relval': '',
            'runUnscheduled': False,
            'fragment_name': '',
            'scenario': '',
            'step': [],
        },
        # Events per lumi - if empty, events per job will be used
        'events_per_lumi': '',
        # GPU parameters
        'gpu': {
            'requires': 'forbidden',
            'gpu_memory': '',
            'cuda_capabilities': [],
            'cuda_runtime': '',
            'gpu_name': '',
            'cuda_driver_version': '',
            'cuda_runtime_version': ''
        },
        # Input file info
        'input': {
            'dataset': '',
            'lumisection': {},
            'run': [],
            'label': '',
        },
        # Keeping output of this task
        'keep_output': True,
        # Lumis per job - applicable to non-first steps
        'lumis_per_job': '',
        # Actual globaltag, resolved from auto:... conditions
        'resolved_globaltag': '',
        # Overwrite default CMSSW scram arch
        'scram_arch': '',
    }

    lambda_checks = {
        'cmssw_release': lambda cmssw: not cmssw or ModelBase.lambda_check('cmssw_release')(cmssw),
        'config_id': lambda cid: ModelBase.matches_regex(cid, '[a-f0-9]{0,50}'),
        '_driver': {
            'conditions': lambda c: not c or ModelBase.matches_regex(c, '[a-zA-Z0-9_]{0,50}'),
            'era': lambda e: not e or ModelBase.matches_regex(e, '[a-zA-Z0-9_\\,]{0,50}'),
            'scenario': lambda s: not s or s in {'pp', 'cosmics', 'nocoll', 'HeavyIons'},
        },
        '_gpu': {
            'requires': lambda r: r in ('forbidden', 'optional', 'required'),
            'cuda_capabilities': lambda l: isinstance(l, list),
            'gpu_memory': lambda m: m == '' or int(m) > 0,
        },
        '_input': {
            'dataset': lambda ds: not ds or ModelBase.lambda_check('dataset')(ds),
            'label': lambda l: not l or ModelBase.lambda_check('label')(l)
        },
        'lumis_per_job': lambda l: l == '' or int(l) > 0,
        'name': lambda n: ModelBase.matches_regex(n, '[a-zA-Z0-9_\\-]{1,150}'),
        'scram_arch': lambda s: not s or ModelBase.lambda_check('scram_arch')(s),
    }

    def __init__(self, json_input=None, parent=None, check_attributes=True):
        if json_input:
            json_input = deepcopy(json_input)
            # Remove -- from argument names
            schema = self.schema()
            if json_input.get('input', {}).get('dataset'):
                json_input['driver'] = schema.get('driver')
                json_input['gpu'] = schema.get('gpu')
                json_input['gpu']['requires'] = 'forbidden'
                step_input = json_input['input']
                for key, default_value in schema['input'].items():
                    if key not in step_input:
                        step_input[key] = default_value
            else:
                json_input['driver'] = {k.lstrip('-'): v for k, v in json_input['driver'].items()}
                json_input['input'] = schema.get('input')
                if json_input.get('gpu', {}).get('requires') not in ('optional', 'required'):
                    json_input['gpu'] = schema.get('gpu')
                    json_input['gpu']['requires'] = 'forbidden'

                driver = json_input['driver']
                for key, default_value in schema['driver'].items():
                    if key not in driver:
                        driver[key] = default_value

                if driver.get('data') and driver.get('mc'):
                    raise  Exception('Both --data and --mc are not allowed in the same step')

                if driver.get('data') and driver.get('fast'):
                    raise Exception('Both --data and --fast are not allowed in the same step')

        ModelBase.__init__(self, json_input, check_attributes)
        if parent:
            self.parent = weakref.ref(parent)
        else:
            self.parent = None

    def get_prepid(self):
        return 'RelValStep'

    def get_short_name(self):
        """
        Return a shortened step name
        GenSimFull for anything that has GenSim in it
        HadronizerFull for anything that has Hadronizer in it
        Split and cut by underscores for other cases
        """
        name = self.get('name')
        if 'gensim' in name.lower():
            return 'GenSimFull'

        if 'hadronizer' in name.lower():
            return 'HadronizerFull'

        while len(name) > 50:
            name = '_'.join(name.split('_')[:-1])
            if '_' not in name:
                break

        return name

    def get_index_in_parent(self):
        """
        Return step's index in parent's list of steps
        """
        for index, step in enumerate(self.parent().get('steps')):
            if self == step:
                return index

        raise Exception(f'Step is not a child of {self.parent().get_prepid()}')

    def get_step_type(self):
        """
        Return whether this is cmsDriver or input file step
        """
        if self.get('input').get('dataset'):
            return 'input_file'

        return 'cms_driver'

    @staticmethod
    def chunkify(items, chunk_size):
        """
        Yield fixed size chunks of given list
        """
        start = 0
        chunk_size = max(chunk_size, 1)
        while start < len(items):
            yield items[start: start + chunk_size]
            start += chunk_size

    def __build_cmsdriver(self, step_index, arguments, for_submission):
        """
        Build a cmsDriver command from given arguments
        Add comment in front of the command
        """
        fragment_name = arguments['fragment_name']
        if not fragment_name:
            fragment_name = f'step{step_index + 1}'

        self.logger.info('Generating %s cmsDriver for step %s', fragment_name, step_index)
        # Actual command
        command = ''
        if not for_submission:
            command += f'# Command for step {step_index + 1}:\n'

        command += f'cmsDriver.py {fragment_name}'
        # Comment in front of the command for better readability
        comment = f'# Arguments for step {step_index + 1}:\n'
        for key in sorted(arguments.keys()):
            if key in ('fragment_name', 'extra'):
                continue

            if not arguments[key]:
                continue

            if isinstance(arguments[key], bool):
                arguments[key] = ''

            if isinstance(arguments[key], list):
                arguments[key] = ','.join([str(x) for x in arguments[key]])

            command += f' --{key} {arguments[key]}'.rstrip()
            comment += f'# --{key} {arguments[key]}'.rstrip() + '\n'

        extra_value = arguments.get('extra')
        if extra_value:
            command += f' {extra_value}'
            comment += f'# <extra> {extra_value}\n'

        # Exit the script with error of cmsDriver.py
        command += ' || exit $?'
        if for_submission:
            return command

        return comment + '\n' + command

    def __build_das_command(self, step_index):
        """
        Build a dasgoclient command to fetch input dataset file names
        """
        input_dict = self.get('input')
        dataset = input_dict['dataset']
        lumisections = input_dict['lumisection']
        if lumisections:
            self.logger.info('Making a DAS command for step %s with lumisection list', step_index)
            files_name = f'step{step_index + 1}_files.txt'
            lumis_name = f'step{step_index + 1}_lumi_ranges.txt'
            comment = f'# Arguments for step {step_index + 1}:\n'
            command = f'# Command for step {step_index + 1}:\n'
            comment += f'#   dataset: {dataset}\n'
            command += f'echo "" > {files_name}\n'
            for run, lumi_ranges in lumisections.items():
                for lumi_range in lumi_ranges:
                    comment += f'#   run: {run}, range: {lumi_range[0]} - {lumi_range[1]}\n'
                    command += 'dasgoclient --limit 0 --format json '
                    command += f'--query "lumi,file dataset={dataset} run={run}"'
                    command += f' | das-selected-lumis.py {lumi_range[0]},{lumi_range[1]}'
                    command += f' | sort -u >> {files_name}\n'

            lumi_json = json.dumps(lumisections)
            command += f'echo \'{lumi_json}\' > {lumis_name}'
            return (comment + '\n' + command).strip()

        runs = input_dict['run']
        if runs:
            self.logger.info('Making a DAS command for step %s with run list', step_index)
            files_name = f'step{step_index + 1}_files.txt'
            comment = f'# Arguments for step {step_index + 1}:\n'
            command = f'# Command for step {step_index + 1}:\n'
            comment += f'#   dataset: {dataset}\n'
            command += f'echo "" > {files_name}\n'
            for run_chunk in self.chunkify(runs, 25):
                run_chunk = ','.join([str(r) for r in run_chunk])
                comment += f'#   runs: {run_chunk}\n'
                command += 'dasgoclient --limit 0 '
                command += f'--query "file dataset={dataset} run in [{run_chunk}]" '
                command += f'>> {files_name}\n'

            return (comment + '\n' + command).strip()

        return f'# Step {step_index + 1} is input dataset for next step: {dataset}'

    def get_command(self, custom_fragment=None, for_submission=False, for_test=False):
        """
        Return a cmsDriver command for this step
        Config file is named like this
        """
        step_type = self.get_step_type()
        index = self.get_index_in_parent()
        if step_type == 'input_file':
            if for_submission:
                return '# Nothing to do for input file step'

            return self.__build_das_command(index)

        arguments_dict = deepcopy(self.get('driver'))
        if custom_fragment:
            arguments_dict['fragment_name'] = custom_fragment

        # No execution
        arguments_dict['no_exec'] = True
        # Handle input/output file names
        arguments_dict['fileout'] = f'"file:step{index + 1}.root"'
        arguments_dict['python_filename'] = f'{self.get_config_file_name()}.py'
        # Add events per lumi to customise_commands
        events_per_lumi = self.get('events_per_lumi')
        if events_per_lumi:
            customise_commands = arguments_dict['customise_commands']
            customise_commands += ';"process.source.numberEventsInLuminosityBlock='
            customise_commands += f'cms.untracked.uint32({events_per_lumi})"'
            arguments_dict['customise_commands'] = customise_commands.lstrip(';')

        # Add number of cpu cores of the RelVal if it is >1 and this is not a harvesting step
        cpu_cores = self.parent().get('cpu_cores')
        if cpu_cores > 1 and not self.has_step('HARVESTING') and not self.has_step('ALCAHARVEST'):
            arguments_dict['nThreads'] = cpu_cores

        all_steps = self.parent().get('steps')
        if index > 0:
            previous = all_steps[index - 1]
            previous_type = previous.get_step_type()
            if previous_type == 'input_file':
                # If previous step is an input file, use it as input
                if for_submission:
                    arguments_dict['filein'] = '"file:_placeholder_.root"'
                else:
                    previous_input = previous.get('input')
                    previous_lumisection = previous_input['lumisection']
                    previous_run = previous_input['run']
                    if previous_lumisection:
                        # If there are lumi ranges, add a file with them and list of files as input
                        arguments_dict['filein'] = f'"filelist:step{index}_files.txt"'
                        arguments_dict['lumiToProcess'] = f'"step{index}_lumi_ranges.txt"'
                    elif previous_run:
                        # If there is a run whitelist, add the file
                        arguments_dict['filein'] = f'"filelist:step{index}_files.txt"'
                    else:
                        # If there are no lumi ranges, use input file normally
                        previous_dataset = previous_input['dataset']
                        arguments_dict['filein'] = f'"dbs:{previous_dataset}"'
            else:
                # If previous step is a cmsDriver, use it's output root file
                input_number = self.get_input_step_index() + 1
                eventcontent_index, eventcontent = self.get_input_eventcontent()
                if eventcontent_index == 0:
                    arguments_dict['filein'] = f'"file:step{input_number}.root"'
                else:
                    arguments_dict['filein'] = f'"file:step{input_number}_in{eventcontent}.root"'

            # Customisation for fetching job report
            if step_type != 'input_file' and for_test:
                customise = arguments_dict.get('customise')
                addMonitoring = 'Configuration/DataProcessing/Utils.addMonitoring'
                customise = ','.join([customise, addMonitoring]) if customise else addMonitoring
                arguments_dict['customise'] = customise
        cms_driver_command = self.__build_cmsdriver(index, arguments_dict, for_submission)
        return cms_driver_command

    def get_test_command(self):
        step_type = self.get_step_type()
        index = self.get_index_in_parent()
        if step_type == 'input_file' or 'HARVESTING' in self.get('driver')['step'][0]:
            return ['']
        report_name = f'REPORT{index+1}'
        command = [f'{report_name}=step_{index+1}_report.xml']
        command += [f'cmsRun -e -j ${report_name} step_{index+1}_cfg.py || exit $? ;']
        # command += [f'python3 -c "import xmltodict; report = xmltodict.parse(open(\'$REPORT{index+1}\').read()); print(report)"']
        command += [f'# Parse values from {report_name} report',
                    f'processedEvents=$(grep -Po "(?<=<Metric Name=\\"NumberEvents\\" Value=\\")(.*)(?=\\"/>)" ${report_name} | tail -n 1)',
                    f'producedEvents=$(grep -Po "(?<=<TotalEvents>)(\\d*)(?=</TotalEvents>)" ${report_name} | tail -n 1)',
                    f'threads=$(grep -Po "(?<=<Metric Name=\\"NumberOfThreads\\" Value=\\")(.*)(?=\\"/>)" ${report_name} | tail -n 1)',
                    f'peakValueRss=$(grep -Po "(?<=<Metric Name=\\"PeakValueRss\\" Value=\\")(.*)(?=\\"/>)" ${report_name} | tail -n 1)',
                    f'peakValueVsize=$(grep -Po "(?<=<Metric Name=\\"PeakValueVsize\\" Value=\\")(.*)(?=\\"/>)" ${report_name} | tail -n 1)',
                    f'totalSize=$(grep -Po "(?<=<Metric Name=\\"Timing-tstoragefile-write-totalMegabytes\\" Value=\\")(.*)(?=\\"/>)" ${report_name} | tail -n 1)',
                    f'totalSizeAlt=$(grep -Po "(?<=<Metric Name=\\"Timing-file-write-totalMegabytes\\" Value=\\")(.*)(?=\\"/>)" ${report_name} | tail -n 1)',
                    f'totalJobTime=$(grep -Po "(?<=<Metric Name=\\"TotalJobTime\\" Value=\\")(.*)(?=\\"/>)" ${report_name} | tail -n 1)',
                    f'totalJobCPU=$(grep -Po "(?<=<Metric Name=\\"TotalJobCPU\\" Value=\\")(.*)(?=\\"/>)" ${report_name} | tail -n 1)',
                    f'eventThroughput=$(grep -Po "(?<=<Metric Name=\\"EventThroughput\\" Value=\\")(.*)(?=\\"/>)" ${report_name} | tail -n 1)',
                    f'avgEventTime=$(grep -Po "(?<=<Metric Name=\\"AvgEventTime\\" Value=\\")(.*)(?=\\"/>)" ${report_name} | tail -n 1)',
                    'if [ -z "$eventThroughput" ]; then',
                    '  eventThroughput=$(bc -l <<< "scale=4; 1 / ($avgEventTime / $threads)")',
                    'fi',
                    'if [ -z "$totalSize" ]; then',
                    '  totalSize=$totalSizeAlt',
                    'fi',
                    'if [ -z "$processedEvents" ]; then',
                    '  processedEvents=$EVENTS',
                    'fi',
                    'cpu_eff=$(bc -l <<< "scale=2; ($totalJobCPU * 100) / ($threads * $totalJobTime)")',
                    'size_per_event=$(bc -l <<< "scale=4; ($totalSize * 1024 / $producedEvents)")',
                    'time_per_event=$(bc -l <<< "scale=4; (1 / $eventThroughput)")',
                    f'echo "Validation report of Step {index + 1} sequence"',
                    'echo "Processed events: $processedEvents"',
                    'echo "Produced events: $producedEvents"',
                    'echo "Threads: $threads"',
                    'echo "Peak value RSS: $peakValueRss MB"',
                    'echo "Peak value Vsize: $peakValueVsize MB"',
                    'echo "Total size: $totalSize MB"',
                    'echo "Total job time: $totalJobTime s"',
                    'echo "Total CPU time: $totalJobCPU s"',
                    'echo "Event throughput: $eventThroughput"',
                    'echo "CPU efficiency: $cpu_eff %"',
                    'echo "Size per event: $size_per_event kB"',
                    'echo "Time per event: $time_per_event sec"'
                    ]
        return command

    def has_step(self, step):
        """
        Return if this RelValStep has certain step in --step argument
        """
        for one_step in self.get('driver')['step']:
            if one_step.startswith(step):
                return True

        return False

    def has_eventcontent(self, eventcontent):
        """
        Return if this RelValStep has certain eventcontent in --eventcontent argument
        """
        return eventcontent in self.get('driver')['eventcontent']

    def get_input_step_index(self):
        """
        Get index of step that will be used as input step for current step
        """
        all_steps = self.parent().get('steps')
        index = self.get_index_in_parent()
        this_is_harvesting = self.has_step('HARVESTING')
        self_step = self.get('driver')['step']
        this_is_alca = self_step and self_step[0].startswith('ALCA')
        self.logger.info('Get input for step %s, harvesting: %s', index, this_is_harvesting)
        for step_index in reversed(range(0, index)):
            step = all_steps[step_index]
            # Harvesting step is never input
            if step.has_step('HARVESTING'):
                continue

            # AlCa step is never input
            step_step = step.get('driver')['step']
            if step_step and step_step[0].startswith('ALCA'):
                continue

            # Harvesting step needs DQM as input
            if this_is_harvesting and not step.has_eventcontent('DQM'):
                continue

            # AlCa step needs RECO as input
            if this_is_alca and not step.has_step('RECO'):
                continue

            return step_index

        name = self.get('name')
        if this_is_harvesting:
            raise Exception('No step with --eventcontent DQM could be found'
                            f'as input for {name} (Harvesting step)')

        if this_is_alca:
            raise Exception('No step with --step RECO could be found '
                            f'as input for {name} (AlCa)')

        raise Exception(f'No input step for {name} could be found')

    def get_input_eventcontent(self, input_step=None):
        """
        Return which eventcontent should be used as input for current RelVal step
        """
        if input_step is None:
            all_steps = self.parent().get('steps')
            input_step_index = self.get_input_step_index()
            input_step = all_steps[input_step_index]

        this_is_harvesting = self.has_step('HARVESTING')
        self_step = self.get('driver')['step']
        this_is_alca = self_step and self_step[0].startswith('ALCA')
        input_step_eventcontent = input_step.get('driver')['eventcontent']
        if this_is_harvesting:
            for eventcontent_index, eventcontent in enumerate(input_step_eventcontent):
                if eventcontent == 'DQM':
                    return eventcontent_index, eventcontent

            raise Exception(f'No DQM eventcontent in the input step {input_step_eventcontent}')

        if this_is_alca:
            for eventcontent_index, eventcontent in enumerate(input_step_eventcontent):
                if eventcontent.startswith('RECO'):
                    return eventcontent_index, eventcontent

            raise Exception(f'No RECO eventcontent in the input step {input_step_eventcontent}')

        input_step_eventcontent = [x for x in input_step_eventcontent if not x.startswith('DQM')]
        return len(input_step_eventcontent) - 1, input_step_eventcontent[-1]

    def get_config_file_name(self):
        """
        Return config file name without extension
        """
        if self.get_step_type() == 'input_file':
            return None

        index = self.get_index_in_parent()
        return f'step_{index + 1}_cfg'

    def get_relval_events(self):
        """
        Split --relval argument to total events and events per job/lumi
        """
        relval = self.get('driver')['relval']
        if not relval:
            raise Exception('--relval is not set')

        relval = relval.split(',')
        if len(relval) < 2:
            raise Exception('Not enough parameters in --relval argument')

        requested_events = int(relval[0])
        events_per = int(relval[1])
        return requested_events, events_per

    def get_release(self):
        """
        Return CMSSW release of the step
        If CMSSW release is not specified, return release of the parent RelVal
        """
        cmssw_release = self.get('cmssw_release')
        if cmssw_release:
            return cmssw_release

        if not self.parent:
            raise Exception('Could not get CMSSW release, because step has no parent')

        cmssw_release = self.parent().get('cmssw_release')
        return cmssw_release

    def get_scram_arch(self):
        """
        Return the scram arch of the step
        If scram arch is not specified, return scram arch of the release
        """
        scram_arch = self.get('scram_arch')
        if scram_arch:
            return scram_arch

        if self.parent:
            scram_arch = self.parent().get('scram_arch')
            if scram_arch:
                return scram_arch

        cmssw_release = self.get_release()
        scram_arch = get_scram_arch(cmssw_release)
        if scram_arch:
            return scram_arch

        raise Exception(f'Could not find SCRAM arch of {cmssw_release}')

    def get_gpu_requires(self):
        """
        Return whether GPU is required, optional of forbidden
        """
        return self.get('gpu')['requires']

    def get_gpu_dict(self):
        """
        Return a dictionary with GPU parameters for ReqMgr2
        """
        gpu_info = self.get('gpu')
        keys = {'cuda_capabilities': 'CUDACapabilities',
                'cuda_runtime': 'CUDARuntime',
                'gpu_name': 'GPUName',
                'cuda_driver_version': 'CUDADriverVersion',
                'cuda_runtime_version': 'CUDARuntimeVersion'}
        params = {key: gpu_info[attr] for attr, key in keys.items() if gpu_info.get(attr)}
        if gpu_info.get('gpu_memory'):
            params['GPUMemoryMB'] = int(gpu_info['gpu_memory'])

        return params