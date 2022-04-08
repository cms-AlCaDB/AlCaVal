import json
import flask
from flask import jsonify, request
from .api_base import APIBase
from application import oidc

class CreateTicketAPI(APIBase):
    def __init__(self):
        APIBase.__init__(self) 
    def put(self):
        print(dict(request.form))
        return {"todo_id": "todos[todo_id]"}

    @oidc.check
    def get(self):
        return {"_id": 5, "title": "HCAL relval"}