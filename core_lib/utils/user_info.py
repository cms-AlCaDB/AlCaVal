import jwt
from flask import request

class UserInfo():
    """
    Holds info of a user.
    Info is obtains from headers supplied by SSO proxy
    """
    def __init__(self):
        self.__user = None
        self.__roles = ['user', 'manager', 'administrator']

    def get_user_info(self):
        """Get user info"""
        if not self.__user:
            raw_token = request.headers.get('X-Forwarded-Access-Token')                 
            if not raw_token:
                raise Exception('Session is expired. Please reload the page!')
            userinfo = jwt.decode(
                                raw_token,
                                options={"verify_signature": False}
                            )
            username = userinfo['sub']
            fullname = userinfo['name']
            name     = userinfo['given_name']
            lastname = userinfo['family_name']
            user_role = 'user'

            for role in reversed(self.__roles):
                if role in userinfo['cern_roles']:
                    user_role = role
                    break

            role_index = self.__roles.index(user_role)
            self.__user = {'name': name,
                            'lastname': lastname,
                            'fullname': fullname,
                            'username': username,
                            'role': user_role,
                            'role_index': role_index}
        return self.__user

    def get_username(self):
        """
        Get username, i.e. login name
        """
        return self.get_user_info()['username']

    def get_user_name(self):
        """
        Get user name and last name
        """
        return self.get_user_info()['fullname']
        
    def get_role(self):
        """
        Get list of groups that user is member of
        """
        return self.get_user_info()['role']

    def role_index_is_more_or_equal(self, role_name):
        """
        Return whether this user has equal or higher role
        """
        return self.__roles.index(role_name) <= self.__roles.index(self.get_role())
