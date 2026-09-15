import { createContext, useContext, useReducer, useEffect } from 'react';
import { AuthService } from '../services/api/AuthService';
import { authReducer, initialAuthState, AUTH_ACTIONS } from '../reducers/authReducer';

const AuthContext = createContext(null);

const DEFAULT_DEMO_USER = { id: 1, name: 'Demo User', role: 'farmer' };

export function AuthProvider({ children }) {
  const [state, dispatch] = useReducer(authReducer, initialAuthState);

  useEffect(() => {
    // Check for existing token and user data on load
    const token = localStorage.getItem('agri_token');
    const storedUser = localStorage.getItem('agri_user');
    
    if (token && storedUser) {
      try {
        dispatch({ type: AUTH_ACTIONS.LOGIN_SUCCESS, payload: JSON.parse(storedUser) });
      } catch (e) {
        dispatch({ type: AUTH_ACTIONS.LOGIN_SUCCESS, payload: DEFAULT_DEMO_USER });
      }
    } else {
      dispatch({ type: AUTH_ACTIONS.LOGOUT });
    }

    // Cross-Tab Logout Synchronization
    const handleStorageChange = (e) => {
      if (e.key === 'agri_token' && e.newValue === null) {
        dispatch({ type: AUTH_ACTIONS.LOGOUT });
        window.location.href = '/';
      }
    };
    window.addEventListener('storage', handleStorageChange);

    return () => window.removeEventListener('storage', handleStorageChange);
  }, []);

  const login = async ({ email, password }) => {
    dispatch({ type: AUTH_ACTIONS.LOGIN_REQUEST });

    try {
       const data = await AuthService.login({ email, password });
       const userPayload = {
         id: data.user.id,
         name: data.user.full_name,
         role: data.user.role.toLowerCase(),
         email: data.user.email
       };
       localStorage.setItem('agri_token', data.access_token);
       localStorage.setItem('agri_user', JSON.stringify(userPayload));
       dispatch({ type: AUTH_ACTIONS.LOGIN_SUCCESS, payload: userPayload });
       return { success: true };
    } catch (e) {
       const errorMsg = e.response?.data?.detail || e.message || 'Invalid credentials';
       dispatch({ type: AUTH_ACTIONS.LOGIN_FAILURE, payload: errorMsg });
       return { success: false, error: errorMsg };
    }
  };

  const register = async (userData) => {
    try {
      const data = await AuthService.register(userData);
      const userPayload = {
        id: data.user.id,
        name: data.user.full_name,
        role: data.user.role.toLowerCase(),
        email: data.user.email
      };
      localStorage.setItem('agri_token', data.access_token);
      localStorage.setItem('agri_user', JSON.stringify(userPayload));
      dispatch({ type: AUTH_ACTIONS.LOGIN_SUCCESS, payload: userPayload });
      return { success: true, user: userPayload };
    } catch (e) {
      const errorMsg = e.response?.data?.detail || e.message || 'Registration failed';
      return { success: false, error: errorMsg };
    }
  };

  const logout = () => {
    localStorage.removeItem('agri_user');
    localStorage.removeItem('agri_token');
    dispatch({ type: AUTH_ACTIONS.LOGOUT });
    window.location.href = '/';
  };

  const triggerSessionExpired = () => {
    localStorage.removeItem('agri_user');
    localStorage.removeItem('agri_token');
    dispatch({ type: AUTH_ACTIONS.SESSION_EXPIRED });
  };

  return (
    <AuthContext.Provider value={{ 
      ...state, 
      login, 
      logout, 
      register,
      triggerSessionExpired
    }}>
      {!state.loading && children}
    </AuthContext.Provider>
  );
}

export const useAuth = () => useContext(AuthContext);
