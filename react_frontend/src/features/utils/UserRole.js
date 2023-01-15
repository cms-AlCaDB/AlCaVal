import axios from 'axios'
import React from 'react';

// Hook for fetching current user info
const useUserRole = () => {
  const userInfo =  React.useRef(undefined);
  React.useEffect(() => fetchUserInfo(), []);

  const fetchUserInfo = () => {
    axios.get('api/system/user_info').then(response => {
      userInfo.current = response.data.response;
    });
  }

  const role  = (roleName) => {
    if (!userInfo.current) {
      return false;
    }
    if (roleName === 'user') {
      return true
    } else if (roleName === 'manager') {
      return userInfo.current.role_index >= 1;
    } else if (roleName === 'administrator') {
      return userInfo.current.role_index >= 2;
    }
  }

  const getUserInfo = () => {
    return userInfo.current;
  }

  return {role, getUserInfo};
}

export default useUserRole;