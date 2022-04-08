from flask_restful import Resource

class APIBase(Resource):
    def __init__(self):
        Resource.__init__(self)

    @staticmethod
    def ensure_role(role_name):
        pass
        
