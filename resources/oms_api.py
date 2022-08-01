# Bunch of methods to access OMS API
#
# Author: Pritam Kalbhor (physics.pritam@gmail.com)
#
# Description: Methods to access CMS-OMS agg api for online run details
# ------------------------------------------------------------------------------

import os
import ast, json
import logging
import requests
import subprocess
from datetime import datetime
from auth_get_sso_cookie import cern_sso
from core_lib.utils.global_config import Config

omsUrl = "https://cmsoms.cern.ch/agg/api/v1/"

class OMSAPI(object):
	def __init__(self):
		self.logger = logging.getLogger()
		self.cookies = OMSAPI.authenticate()

	@staticmethod
	def authenticate():
		"""Make sure Kereberos keytab file is created for authentication
		"""
		try:
			krb_status = subprocess.check_output(['klist', 'alcauser'], shell=True)
			exp_time = krb_status.decode().split('  ')[-2]
			exp_time = datetime.strptime(exp_time, '%m/%d/%Y %H:%M:%S').timestamp()
		except:
			exp_time = 1
		timenow = datetime.now().timestamp()
		if exp_time < timenow: 
			cred_file = Config.get('credentials_file')
			with open(cred_file) as json_file: creds = json.load(json_file)
			user = creds['username']
			os.system(f'kinit -kt {user}.keytab {user}@CERN.CH')

		url = "http://cmsoms.cern.ch"
		session, response = cern_sso.login_with_kerberos(url, False, "auth.cern.ch", False)
		redirect_uri = response.headers["Location"]
		session.get(redirect_uri, verify=False)
		return session.cookies

	def get(self, url):
		return requests.get(url, cookies = self.cookies, verify=False)

	def get_datarates(self, RunNumber, DataSetName):
		self.logger.info(f'Getting datarates for {RunNumber}, {DataSetName}')
		url = omsUrl+"datasetrates?page[limit]=2000&"
		url += "filter[run_number][EQ]={}&filter[dataset_name][EQ]={}".format(RunNumber, DataSetName)
		data = json.loads(self.get(url).content.decode('utf-8'))
		return data

	def get_nEvents(self, DataSetName, RunNumber, LumiSec=''):
		"""Pass LumiSec as a list. e.g. [[1, 50],[100,250]]
		   DataSetName with Just title. e.g. ZeroBias, HLTPhysics"""
		nEvents = 0
		data = self.get_datarates(RunNumber, DataSetName)
		self.logger.info(f'Getting number of events for {RunNumber}, {DataSetName}')
		if LumiSec == '':
			for v in data['data']: nEvents += v['attributes']['events']
		else:
			LumiSec = ast.literal_eval(LumiSec)
			for LumiRange in LumiSec:
				for i, v in enumerate(data['data']):
					a, b = LumiRange
					if not i in range(a-1, b): continue
					nEvents += v['attributes']['events']
		return nEvents

	def get_run_details(self, RunNumber, LumiSec=''):
		"""Get run details. Also gets class of the run(very novice)"""
		url = omsUrl+"runs/{}".format(RunNumber)
		data = json.loads(self.get(url).content.decode('utf-8'))

		lumi_data = self.get_lumi_details(RunNumber)

		LumiSec = ast.literal_eval(LumiSec)
		percent = 1; flipped = False
		for LumiRange in LumiSec:
			for i, v in enumerate(lumi_data['data']):
				a, b = LumiRange
				if not i in range(a-1, b): continue
				beam1_present = v['attributes']['beam1_present']
				beam2_present = v['attributes']['beam2_present']
				beam1_stable = v['attributes']['beam1_stable']
				beam2_stable = v['attributes']['beam2_stable']
				beam = bool(beam1_present and beam2_present and beam1_stable and beam2_stable)
				if not (beam or flipped):  percent = 0
				percent = (int(percent) + int(beam))/2.
				if flipped == False: flipped = True
		data['data']['class'] = 'Collisions' if percent*100 > 95 else 'Cosmics'
		return data

	def get_lumi_details(self, RunNumber):
		url = omsUrl+"runs/{}/lumisections?page[limit]=2000".format(RunNumber)
		data = json.loads(self.get(url).content.decode('utf-8'))
		return data