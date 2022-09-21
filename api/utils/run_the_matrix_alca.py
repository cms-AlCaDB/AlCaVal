"""
PdmV's simplified implementation of runTheMatrix.py used for AlCaDB
"""
from __future__ import print_function
import sys
import argparse
import json
import importlib
import inspect
import re
#pylint: disable=wrong-import-position,import-error
import Configuration.PyReleaseValidation.relval_steps as steps_module
import alcaval_steps as alcasteps_module
from Configuration.PyReleaseValidation.MatrixInjector import MatrixInjector
#pylint: enable=wrong-import-position,import-error


def clean_split(string, separator=','):
    """
    Split a string by separator and collect only non-empty values
    """
    return [x.strip() for x in string.split(separator) if x.strip()]


def get_wmsplit():
    """
    Get wmsplit dictionary from MatrixInjector prepare() method
    """
    try:
        src = MatrixInjector.get_wmsplit()
        return src
    except Exception:
        try:
            src = inspect.getsource(MatrixInjector.prepare)
            src = [x.strip() for x in src.split('\n') if 'wmsplit' in x]
            src = [x.replace(' ', '') for x in src if not x.startswith('#')]
            src = [x for x in src if re.match('wmsplit\\[.*\\]=', x)]
            src = [x.replace('wmsplit[\'', '').replace('\']', '') for x in src]
            src = {x[0]: x[1] for x in [x.split('=') for x in src]}
            return src
        except Exception as ex:
            print(ex)
            return {}


def extract_events_per_lumi(step):
    """
    Extract process.source.numberEventsInLuminosityBlock value from a step it it exists
    """
    customise_commands = step.get('--customise_commands', '')
    if 'process.source.numberEventsInLuminosityBlock' not in customise_commands:
        return None

    regex = 'process.source.numberEventsInLuminosityBlock=cms.untracked.uint32\\(([0-9]*)\\)'
    events_per_lumi = re.findall(regex, customise_commands)
    if not events_per_lumi or not events_per_lumi[-1].isdigit():
        return None

    events_per_job = int(step.get('--relval', '').split(',')[1])
    events_per_lumi = int(events_per_lumi[-1])
    customise_commands = re.sub(regex, '', customise_commands).replace('""', '')
    if not customise_commands:
        del step['--customise_commands']
    else:
        step['--customise_commands'] = customise_commands

    # Events per lumi has to be less or equal to events per job
    return min(events_per_lumi, events_per_job)


def split_command_to_dict(command):
    """
    Split string command into a dictionary
    """
    command_dict = {}
    # Split by spaces
    command = [x for x in command.strip().split(' ') if x.strip()]
    # Split by equal signs
    command = [x.split('=', 1) for x in command]
    # Flatten the list
    command = [x for command_part in command for x in command_part]
    for index, value in enumerate(command):
        if value.startswith('-'):
            if index + 1 < len(command) and not command[index + 1].startswith('-'):
                command_dict[value] = command[index + 1]
            else:
                command_dict[value] = ''

    return command_dict


def get_workflows_module(name):
    """
    Load a specified module from Configuration.PyReleaseValidation
    """
    workflows_module_name = 'Configuration.PyReleaseValidation.relval_' + name
    if name=='alca':
        workflows_module_name = 'relval_' + name
    workflows_module = importlib.import_module(workflows_module_name)
    print('Loaded %s. Found %s workflows inside' % (workflows_module_name,
                                                    len(workflows_module.workflows)))
    return workflows_module


def get_workflow_name(matrix):
    """
    Get workflow name if it is present
    """
    workflow_name = matrix[0]
    if isinstance(workflow_name, list):
        if workflow_name:
            workflow_name = workflow_name[0]
        else:
            workflow_name = ''

    print('Workflow name: %s' % (workflow_name))
    return workflow_name


def should_apply_additional_command(workflow_step, command_steps):
    """
    Return whether workflow step includes steps specified in "command_steps"
    and should have additional command applied to it
    """
    if not command_steps:
        return True

    if '-s' in workflow_step:
        steps = workflow_step['-s']
    elif '--step' in workflow_step:
        steps = workflow_step['--step']
    else:
        return True

    steps = set(clean_split(steps))
    should_apply = len(command_steps & steps) > 0
    print('Workflow step steps: %s, command_steps: %s, should apply: %s',
          steps,
          command_steps,
          should_apply)
    return should_apply


def merge_additional_command(workflow_step, command):
    """
    Merge workflow arguments with additional parameters provided by user
    """
    command_dict = split_command_to_dict(command)
    if '--step' in command_dict:
        command_dict['-s'] = command_dict.pop('--step')

    if '--number' in command_dict:
        command_dict['-n'] = command_dict.pop('--number')

    print('Merging user commands %s' % (command_dict))
    print('Merging to %s' % (workflow_step))
    return steps_module.merge([command_dict, workflow_step])


def make_relval_step(workflow_step, workflow_step_name, wmsplit):
    """
    Build one workflow step - either input dataset or cmsDriver
    """
    step = {'name': workflow_step_name}
    if workflow_step_name in wmsplit:
        step['lumis_per_job'] = wmsplit[workflow_step_name]
    elif 'INPUT' in workflow_step:
        step['lumis_per_job'] = workflow_step['INPUT'].split
    else:
        # Default changed from 10 to 5
        step['lumis_per_job'] = 5

    if 'INPUT' in workflow_step:
        # This step has input dataset
        step_input = workflow_step['INPUT']
        step['input'] = {'dataset': step_input.dataSet,
                         'lumisection': step_input.ls,
                         'run': step_input.run,
                         'label': step_input.label,
                         'events': step_input.events}
    else:
        # This is cmsDriver step
        # Rename some arguments
        if '-s' in workflow_step:
            workflow_step['--step'] = workflow_step.pop('-s')

        if 'cfg' in workflow_step:
            workflow_step['fragment_name'] = workflow_step.pop('cfg')

        if '-n' in workflow_step:
            workflow_step['--number'] = workflow_step.pop('-n')

        # Change "flags" value to True, e.g. --data, --mc, --fast
        for arg_name, arg_value in workflow_step.items():
            if arg_value == '':
                workflow_step[arg_name] = True

        events_per_lumi = extract_events_per_lumi(workflow_step)
        if events_per_lumi:
            step['events_per_lumi'] = events_per_lumi

        step['arguments'] = workflow_step

    print(step)
    return step

def main():
    """
    Main
    """
    parser = argparse.ArgumentParser()
    parser.add_argument('-l', '--list',
                        dest='workflow_ids',
                        help='Comma separated list of workflow ids')
    parser.add_argument('-w', '--what',
                        dest='matrix_name',
                        help='RelVal workflows file: standard, upgrade, ...')
    parser.add_argument('-c', '--command',
                        dest='command',
                        help='Additional command to add to each cmsDriver')
    parser.add_argument('-cs', '--command_steps',
                        dest='command_steps',
                        help='Specify which RelVal steps should have additional command applied',
                        default='')
    parser.add_argument('-o', '--output',
                        dest='output_file',
                        help='Output file name')
    parser.add_argument('-r', '--recycle_gs',
                        dest='recycle_gs',
                        action='store_true',
                        help='Recycle GS')

    opt = parser.parse_args()

    workflow_ids = sorted(list({float(x) for x in opt.workflow_ids.split(',')}))
    print('Given workflow ids (%s): %s' % (len(workflow_ids), workflow_ids))
    print('Workflows file: %s' % (opt.matrix_name))
    print('User given command: %s (%s)' % (opt.command, opt.command_steps))
    print('Output file: %s' % (opt.output_file))
    print('Recycle GS: %s' % (opt.recycle_gs))

    workflows_module = get_workflows_module(opt.matrix_name)
    command_steps = set(clean_split(opt.command_steps))
    # wmsplit is a dictionary with LumisPerJob values
    wmsplit = get_wmsplit()
    workflows = {}
    for workflow_id in workflow_ids:
        print('Getting %s workflow' % (workflow_id))
        # workflow_matrix is a list where first element is the name of workflow
        # and second element is list of step names
        # if workflow name is not present, first step name is used
        if workflow_id not in workflows_module.workflows:
            print('Can\'t find %s in %s matrix' % (workflow_id, opt.matrix_name), file=sys.stderr)
            sys.exit(1)

        workflow_matrix = workflows_module.workflows[workflow_id]
        print('Matrix: %s' % (workflow_matrix))
        workflows[workflow_id] = {'steps': [], 'workflow_name': get_workflow_name(workflow_matrix)}
        if workflow_matrix.overrides:
            print('Overrides: %s' % (workflow_matrix.overrides))

        # Go through steps and get the arguments
        steps = steps_module.steps | alcasteps_module.steps
        for workflow_step_index, workflow_step_name in enumerate(workflow_matrix[1]):
            print('\nStep %s. %s' % (workflow_step_index + 1, workflow_step_name))
            if workflow_step_index == 0 and opt.recycle_gs:
                # Add INPUT to step name to recycle GS
                workflow_step_name += 'INPUT'
                print('Step name changed to %s to recycle input' % (workflow_step_name))

            if workflow_step_name not in steps:
                print('Could not find %s in steps module' % (workflow_step_name),
                      file=sys.stderr)
                sys.exit(1)

            # Merge user command, workflow and overrides
            workflow_step = steps[workflow_step_name]
            if workflow_step is None:
                print('Workflow step %s is none, skipping it' % (workflow_step_name))
                continue

            # Because first item in the list has highest priority
            print('Step: %s' % (workflow_step))
            workflow_step = steps_module.merge([workflow_matrix.overrides,
                                                workflow_step])
            if opt.command and should_apply_additional_command(workflow_step, command_steps):
                workflow_step = merge_additional_command(workflow_step, opt.command)

            workflows[workflow_id]['steps'].append(make_relval_step(workflow_step,
                                                                    workflow_step_name,
                                                                    wmsplit))

        # Additional newline inbetween each workflow
        print('\n')

    print('All workflows:')
    print(json.dumps(workflows, indent=2, sort_keys=True))
    if opt.output_file:
        with open(opt.output_file, 'w') as workflows_file:
            json.dump(workflows, workflows_file)


if __name__ == '__main__':
    main()