import re
import ast
import json
import logging
from flask_wtf import FlaskForm
from wtforms import SubmitField
from wtforms.validators import DataRequired, ValidationError, StopValidation, NumberRange

from core_lib.utils.global_config import Config
from core_lib.utils.common_utils import ConnectionWrapper
import requests
from resources.custom_form_fields import (CustomSelect,
                                          SIntegerField,
                                          SSelectField,
                                          SStringField,
                                          STextAreaField
                                         )
from resources.oms_api import OMSAPI
import urllib, urllib3
import os
import logging

class Tier0Api(object):
    def __init__(self):
        self.express_url = 'https://cmsweb.cern.ch/t0wmadatasvc/prod/express_config'
        self.prompt_url = 'https://cmsweb.cern.ch/t0wmadatasvc/prod/reco_config'
        self.stream_done_url = "https://cmsweb.cern.ch/t0wmadatasvc/prod/run_stream_done"
        self.fcsr_url = "https://cmsweb.cern.ch/t0wmadatasvc/prod/firstconditionsaferun"
        self.session = requests.Session()
        request = requests.Request('GET', self.express_url)  # URL will be overwritten anyway
        self.request = self.session.prepare_request(request)
        requests.packages.urllib3.disable_warnings(requests.packages.urllib3.exceptions.InsecureRequestWarning)
        self.logger = logging.getLogger(__name__)

    def process_request(self, url):
        self.request.url = url
        # at the moment the authorization is not required, but it might be in the future
        # this is the way to handle it
        
        grid_cert = Config.get('grid_user_cert')
        grid_key = Config.get('grid_user_key')
        response = self.session.send(self.request, verify=False, cert=(grid_cert, grid_key))
        # if there is a problem with the service (usually 503) print the reason
        response.raise_for_status()
        return response.json()

    def get_run_prompt_config(self):
        url = 'https://cmsweb.cern.ch/t0wmadatasvc/prod/reco_config'
        t0_configs = self.process_request(url)
        ret = t0_configs['result']
        return ret[0]

    def get_run_info(self):
        """Get latest cmssw version in production"""
        tier0_config = self.get_run_prompt_config()
        result = dict()
        result['cmssw'] = tier0_config['cmssw']
        return result

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
grid_cert = Config.get('grid_user_cert')
grid_key = Config.get('grid_user_key')
cmsweb_url = 'https://cmsweb.cern.ch'


class GTDataRequired(object):
    """Validator for Common Prompt GT
    """
    def __init__(self, message=None):
        self.message = message
        self.field_flags = {}

    def __call__(self, form, field):
        hltgt = bool(form.data['hlt_gt'].strip()=='')
        if field.data and (not isinstance(field.data, str) or field.data.strip()) and not hltgt:
            return
        if hltgt:
            return

        if self.message is None:
            message = field.gettext("This field is required.")
        else:
            message = self.message

        field.errors[:] = []
        raise StopValidation(message)

class TicketForm(FlaskForm):
    label_rkw = {'class': 'col-form-label-sm'}
    classDict = {'class': 'form-control form-control-sm'}

    def validate_batch_name(form, field):
        invalid_chars = ['-', ' ', ',', ';', ':']
        if any(char in field.data for char in invalid_chars):
            raise ValidationError("Invalid batch name. Batch name must not contain spaces, hyphens, semicolons, or colons.")

    # Get CMSSW info
    t0api = Tier0Api()
    t0config = t0api.get_run_info()

    prepid = SStringField(
                render_kw=classDict | {'disabled':''},
                label="Prep ID",
                label_rkw = label_rkw
                )
    
    batch_name = SStringField('Batch Name',
                validators=[DataRequired(message="Please provide appropriate batch name"), validate_batch_name],
                render_kw= classDict | {"placeholder": "Subsystem name or DPG/POG. e.g. Tracker"},
                label_rkw={'class': 'col-form-label-sm required'}
                )

    cmssw_release = SStringField('CMSSW Release',
                default=t0config['cmssw'],
                validators=[DataRequired(message="Please provide correct CMSSW release")],
                render_kw = classDict | {"placeholder":"E.g CMSSW_12_3_..."},
                label_rkw = {'class': 'col-form-label-sm required'}
                )
            
    jira_ticket = SSelectField('Jira Ticket', 
                choices=[["", "Select Jira ticket to associated with this"], ["None", "Select nothing for a moment"]],
                validators=[DataRequired(message="Please select Jira ticket out of given list. Or choose to create new")],
                widget=CustomSelect(),
                default='',
                render_kw = classDict | {'option_attr': {"jira_ticket-0": {"disabled": True, "hidden": True}} },
                label_rkw = label_rkw
                )
    label = SStringField('Label (--label)',
                render_kw = classDict | {'placeholder': 'This label will be included in ReqMgr2 workflow name'},
                label_rkw = label_rkw
                )

    title = SStringField('Title',
                validators=[],
                render_kw = classDict | {"placeholder":"Title/purpose of the validation"},
                label_rkw = label_rkw
                )
    cms_talk_link = SStringField('CMS-Talk link',
                validators=[],
                render_kw = classDict | {"placeholder":"Put a link from where this validation was requested"},
                label_rkw = label_rkw
                )
    hlt_menu = SStringField('Custom HLT Menu',
                render_kw = classDict | {"id":"hlt_menu", "placeholder":"Custom HLT menu"},
                label_rkw = label_rkw
                )
    hlt_gt = SStringField('Target HLT GT',
                validators=[],
                render_kw = classDict | {"id":"hlt_gt", "placeholder":"HLT target global tag"},
                label_rkw = label_rkw
                )
    common_prompt_gt_for_hlt = SStringField('Common Prompt GT for target HLT',
                validators=[GTDataRequired(message="Since you have chosen to use HLT global tag, you are required to provide common prompt global tag for the target HLT, which is to be used in RECO step of workflow")],
                render_kw=classDict | {'placeholder': 'Global tag to be used in RECO step for target HLT'},
                label_rkw={'class': 'col-form-label-sm'}
                )
    hlt_gt_ref = SStringField('Reference HLT GT',
                validators=[],
                render_kw = classDict | {"id":"hlt_gt_ref", "placeholder":"HLT reference global tag"},
                label_rkw = label_rkw
                )
    common_prompt_gt_for_hlt_ref = SStringField('Common Prompt GT for reference HLT',
                validators=[GTDataRequired(message="Since you have chosen to use HLT global tag, you are required to provide common prompt global tag for reference HLT, which is to be used in RECO step of workflow")],
                render_kw=classDict | {'placeholder': 'Global tag to be used in RECO step for reference HLT'},
                label_rkw=label_rkw
                )
    prompt_gt = SStringField('Target Prompt GT',
                render_kw = classDict | {'placeholder': 'Prompt target global tag'},
                label_rkw = label_rkw
                )
    prompt_gt_ref = SStringField('Reference Prompt GT',
                render_kw = classDict | {'placeholder': 'Prompt reference global tag'},
                label_rkw = label_rkw
                )
    express_gt = SStringField('Target Express GT',
                render_kw = classDict | {'placeholder': 'Express target global tag'},
                label_rkw = label_rkw
                )
    express_gt_ref = SStringField('Reference Express GT',
                render_kw = classDict | {'placeholder': 'Express reference global tag'},
                label_rkw = label_rkw
                )
    input_datasets = STextAreaField('Datasets', validators=[],
                        render_kw = classDict | {"rows": 6, 'style': 'padding-bottom: 5px;',
                        'placeholder': 'Comma or line separated datasets. e.g: \
                         \n/HLTPhysics/Run2022C-v1/RAW, /ZeroBias/Run2022C-v1/RAW \
                         \n/JetHT/Run2022C-v1/RAW'
                        },
                        label_rkw = label_rkw
                        )
    input_runs = STextAreaField('Run numbers', validators=[],
                        render_kw = classDict | {"rows": 6, 'style': 'padding-bottom: 5px;',
                        'placeholder': 'Comma separated list of run numbers e.g. 346512, 346513 \
                         \nOr\nLumisections in JSON format. e.g. {"354553": [[1, 300]]}',
                        'oninput': 'validateJSON_or_List(this.id)'
                        },
                        label_rkw = label_rkw
                        )
    


    # command = SStringField('Command (--command)',
    #             render_kw = classDict | {"placeholder":"Arguments that will be added to all cmsDriver commands"},
    #             label_rkw = {'class': 'col-form-label-sm'}
    #             )
    # command_steps = SStringField('Command Steps',
    #             render_kw = classDict | {"placeholder":"E.g. RAW2DIGI, L1Reco, RECO, DQM"},
    #             label_rkw = {'class': 'col-form-label-sm'}
    #             )
    cpu_cores = SIntegerField('CPU Cores (-t)', default=4, validators=[NumberRange(min=1, max=16)],
                render_kw = classDict,
                label_rkw = {'class': 'col-form-label-sm'}
                )

    memory = SIntegerField('Memory', default=8000, validators=[NumberRange(min=0, max=30000)],
                render_kw = classDict | {'step': 1000},
                label_rkw = {'class': 'col-form-label-sm'}
                )
    n_streams = SIntegerField('Streams (--nStreams)', default=2, validators=[NumberRange(min=0, max=16)],
                render_kw = classDict,
                label_rkw = {'class': 'col-form-label-sm'}
                )
    matrix_choices = [
        ['alca', 'alca'], ['standard', 'standard'], ['production', 'production'], ['upgrade', 'upgrade'], 
        ['generator', 'generator'], ['pileup', 'pileup'], ['premix', 'premix'],
        ['extendedgen', 'extendedgen'], ['gpu', 'gpu']
    ]
    matrix = SSelectField('Matrix (--what)', choices=matrix_choices,
                           validators=[DataRequired()],
                           default='alca',
                           render_kw = classDict,
                           label_rkw = label_rkw
                        )
    workflow_ids = SStringField('Workflow IDs', validators=[DataRequired()],
                        default='6.51, 6.52',
                        render_kw = classDict | {'placeholder': 'Workflow IDs separated by comma. E.g. 1.1,1.2'},
                        label_rkw = {'class': 'col-form-label-sm'}
                        )
    notes = STextAreaField('Notes',  
                           render_kw = classDict | {
                            "rows": 5,
                            'style': 'padding-bottom: 5px;',
                            'placeholder': "Description of the request. TWiki links etc.."
                           },
                           label_rkw = label_rkw
                      )
    submit = SubmitField('Save Ticket')

    # Validators
    def validate_cmssw_release(self, field):
        url = f'https://api.github.com/repos/cms-sw/cmssw/releases/tags/{field.data}'
        status_code = requests.head(url).status_code
        if status_code != 200:
            raise ValidationError('CMSSW release is not valid!')

    def validate_input_datasets(self, field, test=None):
        if not field.data:
            test_datasets = list()
        else:
            test_datasets = field.data.replace(',', '\n').split('\n')
            test_datasets = list(map(lambda x: x.strip(), test_datasets))
            test_datasets = list((filter(lambda x: len(x)>0, test_datasets)))
        wrong_datasets = list()
        with ConnectionWrapper(cmsweb_url, grid_cert, grid_key) as dbs_conn:
            for dataset in test_datasets:
                regex = r'^/[a-zA-Z0-9\-_]{1,99}/[a-zA-Z0-9\.\-_]{1,199}/[A-Z\-]{1,50}$'
                if not re.fullmatch(regex, dataset):
                    wrong_datasets.append(dataset)
                    continue
                res = dbs_conn.api(
                        'GET',
                        f'/dbs/prod/global/DBSReader/datasets?dataset={dataset}'
                        )
                res = json.loads(res.decode('utf-8'))
                if not res: wrong_datasets.append(dataset)
        if wrong_datasets and not test:
            raise ValidationError(f'Invalid datasets: {", ".join(wrong_datasets)}')
        elif (not field.data.strip()) and self.input_runs.data and (not test):
            raise ValidationError(f"Input dataset field is required when 'Run numbers' are provided")

        # This is to test if this validator is successfull from another validator
        if not (wrong_datasets or ((not field.data) and self.input_runs.data)) and test: 
            return test_datasets
        else:
            return False

    def validate_input_runs(self, field):
        try:
            if not field.data:
                test_runs = list()
            elif not ('{' in field.data and '}' in field.data):
                test_runs = list(map(lambda x: x.strip(), field.data.split(',')))
            elif isinstance(ast.literal_eval(field.data), dict):
                test_runs = list(ast.literal_eval((field.data)).keys())
            else: raise Exception
        except Exception as e:
            raise ValidationError('Accepted only comma separated list of runs \
                                    or JSON formatted lumisections')
        wrong_runs = list()
        with ConnectionWrapper(cmsweb_url, grid_cert, grid_key) as dbs_conn:
            for run in test_runs:
                if not re.fullmatch(r'^\d{6}$', run):
                    wrong_runs.append(run)
                    continue
                res = dbs_conn.api(
                        'GET',
                        f'/dbs/prod/global/DBSReader/runs?run_num={run}'
                        )
                res = json.loads(res.decode('utf-8'))
                if not res: wrong_runs.append(run)
        if wrong_runs:
            raise ValidationError(f'Invalid runs: {", ".join(wrong_runs)}')
        if (not field.data.strip()) and self.input_datasets.data:
            raise ValidationError(f"Run numbers field is required when 'Dataset' field is provided")

        # Test if given runs are available in all datasets
        input_datasets = self.validate_input_datasets(self.input_datasets, test=True)
        if input_datasets:
            incompatible_runs = {d: [] for d in input_datasets}
            with ConnectionWrapper(cmsweb_url, grid_cert, grid_key) as dbs_conn:
                for dataset in input_datasets:
                    runs_in_dataset = dbs_conn.api(
                            'GET',
                            f'/dbs/prod/global/DBSReader/runs?dataset={dataset}'
                            )
                    res = json.loads(runs_in_dataset.decode('utf-8'))
                    res = {a_dict['run_num'] for a_dict in res}
                    bad_runs = list(set([int(a) for a in test_runs]).difference(res))
                    incompatible_runs[dataset] = bad_runs
            if [v for _, v in incompatible_runs.items() if v]:
                msg = ""
                for k, v in incompatible_runs.items():
                    if v:
                        msg += f"Run/s {', '.join([str(l) for l in v])} is/are not present in {k}.\n"
                raise ValidationError(msg)
        else:
            return

        # Validate if lumisections range is correctly casted
        runs = ast.literal_eval(field.data)
        if isinstance(runs, dict):
            for _, value in runs.items():
                is_list = isinstance(value, list)
                is_int = all(
                 (len(items) == 2 if isinstance(items, list) else False) and\
                 isinstance(items, list) and \
                 all(isinstance(item, int) for item in items) for items in value
                )
                if is_list and is_int:
                    lsec = []
                    for v in value: lsec += v
                    asc_range = True if lsec == sorted(lsec) else False
                else:
                    asc_range = False
                if not (is_list and is_int and asc_range):
                    raise ValidationError(
                        f'Lumisections format is not valid. \
                        It should be list of list of lumisection ranges. \
                        e.g. [[1 ,40],[100, 200]]'
                        )

        # Validating number of events
        try:
            oms = OMSAPI()
            stats = {}
            for dataset in input_datasets:
                dname = dataset.split('/')[1].strip()
                events = 0
                for run in test_runs:
                    if isinstance(runs, dict):
                        events += oms.get_nEvents(dname, run, LumiSec=str(runs[run]))
                    else:
                        events += oms.get_nEvents(dname, run)
                stats[dataset] = events
            emptysets = []
            for dataset, events in stats.items():
                if events < 5000: emptysets.append(dataset)
            if emptysets:
                msg = "<ul>"
                for dataset, events in stats.items():
                    msg += f"<li>{dataset}: \
                    <span style='color:blue'>{events}</span> events</li>"
                msg += "</ul>"
                raise ValidationError(
                     f"Too few events in dataset: \
                     {', '.join([d.split('/')[1] for d in emptysets])} {msg}"
                    )

        except Exception as e:
            if isinstance(e, ValidationError): raise
            logging.getLogger().error(e)
