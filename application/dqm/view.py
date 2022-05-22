import json
import requests
from flask import Blueprint, render_template, redirect, request, flash, url_for, session, make_response
from .. import oidc, get_userinfo

dqm_blueprint = Blueprint('dqm', __name__, template_folder='templates', static_folder='static')

@dqm_blueprint.route('/dqm')
@oidc.check
def index():
    user = get_userinfo()
    return render_template('DQMHome.html.jinja', user_name=user['response']['fullname'], user=user)

from .ComparisonForm import ComparisonForm

@dqm_blueprint.route('/dqm/compare', methods=['GET', 'PUT', 'POST'])
@oidc.check
def compare_dqm():
    user = get_userinfo()
    form = ComparisonForm()
    jira = [['CMSALCA-158', 'CMSALCA-158: [HLT] Full track validation of Update of EGM HLT regression tags for Run3 collisions (Week 15, 2022)']]
    new_data = [['1', '/MinimumBias/CMSSW_12_2_1-2022_02_23_21_32_HLTnewco_122X_dataRun3_HLTNew_TkAli_w8_2022_v1-v1/DQMIO']]
    ref_data = [['2', '/MinimumBias/CMSSW_12_2_1-2022_02_23_21_32_HLTrefer_122X_dataRun3_HLT_v4-v1/DQMIO']]
    form.jira_ticket.choices = form.jira_ticket.choices + jira
    form.target_dataset.choices = form.target_dataset.choices + new_data
    form.reference_dataset.choices = form.reference_dataset.choices + ref_data
    if form.validate_on_submit():
        return redirect(url_for('dqm.dqm_plots'))
    return render_template('SubmitForComparison.html.jinja', user_name=user['response']['fullname'], form=form, userinfo=user['response'])

# Tickets table
from .DQMTable import DQMTable

@dqm_blueprint.route('/dqm/plots', methods=['GET'])
@oidc.check
def dqm_plots():
    user = get_userinfo()
    items = [{'dataset': '/MinimumBias/CMSSW_12_2_1-2022_02_23_21_32_HLTnewco_122X_dataRun3_HLTNew_TkAli_w8_2022_v1-v1/DQMIO', 
                'dqmlink': 'https://tinyurl.com/y2wwwwsw',
                'jira_ticket': 'CMSALCA-158', 
                'ticket': 'CMSSW_12_3_0__TestBatch-00001', 
                'relval': 'CMSSW_12_3_0__TestBatch-RunZeroBias2017C-00001'},
             {'dataset': '/MinimumBias/CMSSW_12_2_1-2022_02_23_21_32_HLTrefer_122X_dataRun3_HLT_v4-v1/DQMIO', 
                'dqmlink': 'https://tinyurl.com/yyr8tv8m',
                'jira_ticket': 'CMSALCA-158', 
                'ticket': 'CMSSW_12_3_0__TestBatch-00001', 
                'relval': 'CMSSW_12_3_0__TestBatch-RunZeroBias2017C-00001'}
            ]
    table = DQMTable(items, classes=['table', 'table-hover'])
    return render_template('DQMPlots.html.jinja', user_name=user['response']['fullname'], table=table, userinfo=user['response'])