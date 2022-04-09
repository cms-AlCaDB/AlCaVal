import json
from flask import make_response
from flask_restful import Resource
from .utils.user_info import UserInfo

class APIBase(Resource):
    def __init__(self):
        Resource.__init__(self)

    @staticmethod
    def ensure_role(role_name):
        """
        Ensure that user has appropriate roles for this API call
        """
        def ensure_role_wrapper(func):
            """
            Wrapper
            """
            def ensure_role_wrapper_wrapper(*args, **kwargs):
                """
                Wrapper inside wrapper
                """
                user_info = UserInfo()
                if user_info.role_index_is_more_or_equal(role_name):
                    return func(*args, **kwargs)

                return APIBase.output_text({'response': None,
                                            'success': False,
                                            'message': f'User "{user_info.get_username()}" '
                                                       f'has role "{user_info.get_role()}" '
                                                       f'and is not allowed to access this '
                                                       f'API. Required role "{role_name}"'},
                                           code=403)

            ensure_role_wrapper_wrapper.__name__ = func.__name__
            ensure_role_wrapper_wrapper.__doc__ = func.__doc__
            ensure_role_wrapper_wrapper.__role__ = role_name
            return ensure_role_wrapper_wrapper

        return ensure_role_wrapper        


    @staticmethod
    def output_text(data, code=200, headers=None, content_type='application/json'):
        """
        Makes a Flask response with a plain text encoded body
        """
        if content_type == 'application/json':
            resp = make_response(json.dumps(data, indent=2, sort_keys=True), code)
        else:
            resp = make_response(data, code)

        resp.headers.extend(headers or {})
        resp.headers['Content-Type'] = content_type
        resp.headers['Access-Control-Allow-Origin'] = '*'
        return resp