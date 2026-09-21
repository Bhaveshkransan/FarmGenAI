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

const extractUserPayload = (data: any) => {
  const u = data?.user || data || {};
  const token = data?.token || data?.access_token || u?.token || u?.access_token || '';
  const userId = u?.user_id || u?.id || ('user_' + Math.random().toString(36).substring(2, 9));
  const name = u?.name || u?.full_name || 'User';
  const role = String(u?.role || 'buyer').toLowerCase();
  const email = u?.email || '';
  const location = u?.location || '';
  const prefs = u?.preferences || {};

  const buyerPersona = u?.buyer_persona || u?.buyerPersona || prefs?.buyer_persona || (role === 'buyer' ? 'food_processing' : '');
  const businessName = u?.business_name || u?.businessName || prefs?.business_name || (role === 'buyer' ? `${name} Agro Procure` : `${name} Farms`);
  const fssaiLicense = u?.fssai_license || u?.fssaiLicense || prefs?.fssai_license || '';
  const gstin = u?.gstin || prefs?.gstin || '';
  const mandiLicense = u?.mandi_license || prefs?.mandi_license || '';
  const processingCapacity = u?.processing_capacity || prefs?.processing_capacity || '';
  const procurementWindow = u?.procurement_window || prefs?.procurement_window || '';
  const verificationStatus = u?.verification_status || (fssaiLicense || gstin ? 'VERIFIED' : 'PENDING');

  const userPayload = {
    id: userId,
    user_id: userId,
    name: name,
    full_name: name,
    role: role,
    email: email,
    location: location,
    buyerPersona,
    businessName,
    fssaiLicense,
    gstin,
    mandiLicense,
    processingCapacity,
    procurementWindow,
    verificationStatus,
    preferences: prefs
  };
  return { userPayload, token };
};

  const login = async ({ email, password }) => {
    dispatch({ type: AUTH_ACTIONS.LOGIN_REQUEST });

    try {
       const data = await AuthService.login({ email, password });
       const { userPayload, token } = extractUserPayload(data);
       if (token) {
         localStorage.setItem('agri_token', token);
       }
       localStorage.setItem('agri_user', JSON.stringify(userPayload));
       dispatch({ type: AUTH_ACTIONS.LOGIN_SUCCESS, payload: userPayload });
       return { success: true, user: userPayload };
    } catch (e: any) {
       const errorMsg = e.response?.data?.detail || e.message || 'Invalid credentials';
       dispatch({ type: AUTH_ACTIONS.LOGIN_FAILURE, payload: errorMsg });
       return { success: false, error: errorMsg };
    }
  };

  const register = async (userData) => {
    try {
      const data = await AuthService.register(userData);
      const { userPayload, token } = extractUserPayload(data);
      if (token) {
        localStorage.setItem('agri_token', token);
      }
      localStorage.setItem('agri_user', JSON.stringify(userPayload));
      dispatch({ type: AUTH_ACTIONS.LOGIN_SUCCESS, payload: userPayload });
      return { success: true, user: userPayload };
    } catch (e: any) {
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
