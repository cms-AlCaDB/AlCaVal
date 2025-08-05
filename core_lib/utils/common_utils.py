"""
Common utils
"""
import re
import json
import logging
import hashlib
import xml.etree.ElementTree as XMLet

from .ssh_executor import SSHExecutor
from .cache import TimeoutCache
from .connection_wrapper import ConnectionWrapper
from .locker import Locker
from .global_config import Config


# Scram arch cache to save some requests to cmssdt.cern.ch
__scram_arch_cache = TimeoutCache(3600)


def clean_split(string, separator=',', maxsplit=-1):
    """
    Split a string by separator and collect only non-empty values
    """
    return [x.strip() for x in string.split(separator, maxsplit) if x.strip()]


def make_regex_matcher(pattern):
    """
    Compile a regex pattern and return a function that performs fullmatch on
    given value
    """
    compiled_pattern = re.compile(pattern)
    def matcher_function(value):
        """
        Return whether given value fully matches the pattern
        """
        return compiled_pattern.fullmatch(value) is not None

    return matcher_function


def cmssw_setup(cmssw_release, scram_arch=None):
    """
    Return code needed to set up CMSSW environment for given CMSSW release
    Basically, cmsrel and cmsenv commands
    If scram_arch is None, use default arch of CMSSW release
    Releases are put to <scram arch>/<release name> directory
    """
    if scram_arch is None:
        scram_arch = get_scram_arch(cmssw_release)

    if not scram_arch:
        raise Exception(f'Could not find SCRAM arch of {cmssw_release}')

    commands = [f'export SCRAM_ARCH={scram_arch}',
                'source /cvmfs/cms.cern.ch/cmsset_default.sh',
                'ORG_PWD=$(pwd)']
    if cmssw_release.startswith('/'):
        # Path to CMSSW
        commands += [f'if [ ! -r {cmssw_release}/src ]; then echo "Cannot find {cmssw_release}/src"; exit 1; fi']
    else:
        # CMSSW release name
        commands += ['mkdir -p $SCRAM_ARCH',
                     'cd $SCRAM_ARCH',
                     f'if [ ! -r {cmssw_release}/src ] ; then scram p CMSSW {cmssw_release} ; fi']

    commands += [f'cd {cmssw_release}/src',
                 'CMSSW_SRC=$(pwd)',
                 'eval `scram runtime -sh`',
                 'PYTHON_INT="python"',
                 'if [[ $(head -n 1 `which cmsDriver.py`) =~ "python3" ]]; then PYTHON_INT="python3"; fi',
                 'echo "Using "$PYTHON_INT interpreter',
                 'cd $ORG_PWD']

    return '\n'.join(commands)


def config_cache_lite_setup():
    """
    Return code needed to set up ConfigCacheLite and TweakMakerLite
    """
    commands = []
    repo = 'https://github.com/cms-PdmV/ConfigCacheLite.git'
    commands += [f'if [ ! -r ConfigCacheLite ] ; then git clone --quiet {repo} ; fi',
                 'export PYTHONPATH=$(pwd)/ConfigCacheLite/:$PYTHONPATH']
    return '\n'.join(commands)

def get_scram_arch(cmssw_release):
    """
    Get scram arch from
    https://cmssdt.cern.ch/SDT/cgi-bin/ReleasesXML?anytype=1
    Cache it global variable
    """
    if not cmssw_release:
        return None

    cmssw_release = cmssw_release.split('/')[-1]
    cached_releases = __scram_arch_cache.get('releases', {})
    cached_value = cached_releases.get(cmssw_release)
    if cached_value:
        return cached_value

    with Locker().get_lock('get-scram-arch'):
        # Maybe cache got updated while waiting for a lock
        cached_releases = __scram_arch_cache.get('releases', {})
        cached_value = cached_releases.get(cmssw_release)
        if cached_value:
            return cached_value

        with ConnectionWrapper(host='https://cmssdt.cern.ch') as connection:
            response = connection.api('GET', '/SDT/cgi-bin/ReleasesXML?anytype=1')

        root = XMLet.fromstring(response)
        releases = {}
        for architecture in root:
            if architecture.tag != 'architecture':
                # This should never happen as children should be <architecture>
                continue

            scram_arch = architecture.attrib.get('name')
            for release in architecture:
                releases[release.attrib.get('label')] = scram_arch

        __scram_arch_cache.set('releases', releases)

    return releases.get(cmssw_release)


def dbs_datasetlist(query):
    """
    Query DBS datasetlist endpoint with a query of list of datasets
    List of datasets do not support wildcards
    String query supports wildcards
    """
    if not query:
        return []


    if isinstance(query, list):
        query = [ds[ds.index('/'):] for ds in query]
    else:
        query = query[query.index('/'):]

    grid_cert = Config.get('grid_user_cert')
    grid_key = Config.get('grid_user_key')
    with ConnectionWrapper('https://cmsweb-prod.cern.ch:8443', grid_cert, grid_key) as dbs_conn:
        dbs_response = dbs_conn.api('POST',
                                    '/dbs/prod/global/DBSReader/datasetlist',
                                    {'dataset': query,
                                     'detail': 1,
                                     'dataset_access_type': '*'},
                                    headers={'Content-type': 'application/json'})

    dbs_response = json.loads(dbs_response.decode('utf-8'))
    if not dbs_response:
        return []

    return dbs_response


def dbs_dataset_runs(dataset):
    """
    Fetch a list of runs from DBS for a given dataset
    """
    if not dataset:
        return []

    grid_cert = Config.get('grid_user_cert')
    grid_key = Config.get('grid_user_key')
    with ConnectionWrapper('https://cmsweb-prod.cern.ch:8443', grid_cert, grid_key) as dbs_conn:
        with Locker().get_lock('get-dataset-runs'):
            dbs_response = dbs_conn.api('GET',
                                        f'/dbs/prod/global/DBSReader/runs?dataset={dataset}',
                                        headers={'Content-type': 'application/json'})

    dbs_response = json.loads(dbs_response.decode('utf-8'))
    if not dbs_response:
        return []

    runs = [r['run_num'] for r in dbs_response]
    return runs


def change_workflow_priority(workflow_names, priority):
    """
    Change priority of given list of workflow names
    """
    workflow_names = [w.strip() for w in workflow_names if w.strip()]
    if not workflow_names:
        return

    logger = logging.getLogger('logger')
    cmsweb_url = Config.get('cmsweb_url')
    grid_cert = Config.get('grid_user_cert')
    grid_key = Config.get('grid_user_key')
    with ConnectionWrapper(cmsweb_url, grid_cert, grid_key) as cmsweb_connection:
        for workflow in workflow_names:
            logger.info('Changing "%s" priority to %s', workflow, priority)
            response = cmsweb_connection.api('PUT',
                                             f'/reqmgr2/data/request/{workflow}',
                                             {'RequestPriority': priority})
            logger.debug(response)


def sort_workflows_by_name(workflows, name_attr):
    """
    Sort workflows by their submission date
    """
    return sorted(workflows, key=lambda w: '_'.join(w[name_attr].split('_')[-3:]))


def get_workflows_from_reqmgr2_for_prepid(prepid):
    """Fetch workflows from given prepid"""
    if not prepid:
        return []

    cmsweb_url = Config.get('cmsweb_url')
    grid_cert = Config.get('grid_user_cert')
    grid_key = Config.get('grid_user_key')
    headers = {'Content-type': 'application/json',
               'Accept': 'application/json'}
    with ConnectionWrapper(cmsweb_url, grid_cert, grid_key) as cmsweb_connection:
        response = cmsweb_connection.api(
            'GET',
            f'/reqmgr2/data/request?prep_id={prepid}',
            headers=headers
        )
    response = json.loads(response.decode('utf-8'))
    workflows = []
    for res in response['result']:
        for value in res.values():
            workflows.append(value)
    workflows = sort_workflows_by_name(workflows, 'RequestName')
    return workflows


def get_workflows_from_reqmgr2(workflow_names):
    """
    Fetch workflows from ReqMgr2 with given names
    """
    workflow_names = [w.strip() for w in workflow_names if w.strip()]
    if not workflow_names:
        return []

    cmsweb_url = Config.get('cmsweb_url')
    grid_cert = Config.get('grid_user_cert')
    grid_key = Config.get('grid_user_key')
    results = []
    headers = {'Content-type': 'application/json',
               'Accept': 'application/json'}
    with ConnectionWrapper(cmsweb_url, grid_cert, grid_key) as cmsweb_connection:
        for workflow_name in workflow_names:
            response = cmsweb_connection.api(
                'GET',
                f'/reqmgr2/data/request?prep_id={workflow_name}',
                headers=headers
            )
            response = json.loads(response.decode('utf-8'))
            results += response['result']
    workflows = []
    for res in results:
        for value in res.values():
            workflows.append(value)
    workflows = sort_workflows_by_name(workflows, 'RequestName')
    return workflows

def cmsweb_reject_workflows(workflow_status_pairs):
    """
    Reject workflows in ReqMgr2
    Function expects list of tuples where first item is workflow name and second
    is current workflow status
    """
    cmsweb_url = Config.get('cmsweb_url')
    grid_cert = Config.get('grid_user_cert')
    grid_key = Config.get('grid_user_key')
    headers = {'Content-type': 'application/json',
               'Accept': 'application/json'}
    logger = logging.getLogger('logger')
    ignore_status = {'aborted', 'rejected', 'aborted-archived', 'rejected-archived'}
    abort_status = {'assigned', 'staging', 'staged', 'acquired', 'running-open', 'running-closed'}
    with ConnectionWrapper(cmsweb_url, grid_cert, grid_key) as connection:
        for (name, status) in workflow_status_pairs:
            if status in ignore_status:
                continue

            logger.info('%s status is %s', name, status)
            # Depending on current status of workflow,
            # it might need to be either aborted or rejected
            if status in abort_status:
                new_status = 'aborted'
            else:
                new_status = 'rejected'

            logger.info('Will change %s status %s to %s', name, status, new_status)
            response = connection.api('PUT',
                                      f'/reqmgr2/data/request/{name}',
                                      {'RequestStatus': new_status},
                                      headers)
            logger.debug(response)


def run_commands_in_singularity(commands, scram_arch, script_name=None):
    """
    Dump given commands to a script file and run it in a singularity container
    """
    if not script_name:
        script_name = 'singularity-script'

    script_name = script_name.replace(' ', '-')
    bash = [f'# Dump code to {script_name}.sh file that can be run in Singularity',
            f'cat <<\'SingularityScriptFile\' > {script_name}.sh',
            '#!/bin/bash',
            '']
    if isinstance(commands, list):
        while commands and not commands[-1]:
            commands = commands[:-1]

        bash += commands
    else:
        bash += [commands.strip()]

    container_os = clean_split(scram_arch, '_')[0]
    if container_os == 'slc7':
        container_os = 'cc7'

    container_path = '/cvmfs/unpacked.cern.ch/registry.hub.docker.com/cmssw'
    bash += ['',
             f'# End of {script_name}.sh file',
             'SingularityScriptFile',
             '',
             '# Make file executable',
             f'chmod +x {script_name}.sh',
             '',
             f'if [ -e "{container_path}/{container_os}:amd64-latest" ]; then',
             f'  CONTAINER_NAME={container_os}:amd64-latest',
             f'elif [ -e "{container_path}/{container_os}:amd64" ]; then',
             f'  CONTAINER_NAME={container_os}:amd64',
             f'elif [ -e "{container_path}/{container_os}:x86_64-latest" ]; then',
             f'  CONTAINER_NAME={container_os}:x86_64-latest',
             f'elif [ -e "{container_path}/{container_os}:x86_64" ]; then',
             f'  CONTAINER_NAME={container_os}:x86_64',
             'else',
             f'  echo "Could not find amd64 or x86_64 for {container_os}"',
             f'  ls -l {container_path}/{container_os}:*',
             '  exit 1',
             'fi',
             'echo "Using singularity container $CONTAINER_NAME"',
             'export SINGULARITY_CACHEDIR="/tmp/$(whoami)/singularity"',
             '',
             ('singularity run '
              '-B /afs -B /cvmfs -B /eos -B /etc/grid-security '
              f'{container_path}/$CONTAINER_NAME'
              f' $(pwd)/{script_name}.sh')]

    return bash

def run_commands_in_cmsenv(commands, cmssw_version, scram_arch):
    """
    Run given commands in CMS environment in an appropriate container if needed
    """
    os_name, _, gcc_version = clean_split(scram_arch, '_')
    # Always use amd64 architecture
    scram_arch = f'{os_name}_amd64_{gcc_version}'
    # Add cms environment setup
    setup = cmssw_setup(cmssw_version, scram_arch).split('\n')
    if not isinstance(commands, list):
        commands  = [commands.strip()]

    commands = setup + [''] + commands
    if os_name != 'slc7':
        script_hash = get_hash(commands)
        script_name = f'singularity-script-{script_hash}'
        commands = run_commands_in_singularity(commands, scram_arch, script_name)

    commands = '\n'.join(commands)
    return commands


def get_hash(data):
    """
    Get hash of given data
    """
    if isinstance(data, list):
        data = '\n'.join(data)

    return hashlib.md5(data.encode('utf-8')).hexdigest()