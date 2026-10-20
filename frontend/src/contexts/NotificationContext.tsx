import React, { createContext, useContext, useState, useCallback } from 'react';
import { X, Bell } from 'lucide-react';

const NotificationContext = createContext(null);

export function NotificationProvider({ children }) {
  const [notifications, setNotifications] = useState([]);

  const addNotification = useCallback((messageOrType, typeOrMessage = 'info') => {
    let message = messageOrType;
    let type = typeOrMessage;

    const knownTypes = ['success', 'error', 'info', 'warning'];
    if (knownTypes.includes(messageOrType) && typeof typeOrMessage === 'string' && !knownTypes.includes(typeOrMessage)) {
      type = messageOrType;
      message = typeOrMessage;
    }

    const id = Date.now().toString() + '-' + Math.random().toString(36).slice(2, 6);
    setNotifications(prev => [...prev, { id, message: String(message || ''), type }]);
    
    // Auto-dismiss after 5 seconds
    setTimeout(() => {
      setNotifications(prev => prev.filter(n => n.id !== id));
    }, 5000);
  }, []);

  const removeNotification = useCallback((id) => {
    setNotifications(prev => prev.filter(n => n.id !== id));
  }, []);

  // Global API Error Listener
  React.useEffect(() => {
    const handleApiError = (event) => {
      addNotification(event.detail, 'error');
    };
    window.addEventListener('api_error', handleApiError);
    return () => window.removeEventListener('api_error', handleApiError);
  }, [addNotification]);

  return (
    <NotificationContext.Provider value={{ addNotification }}>
      {children}
      
      {/* Toast Container positioned top-right */}
      <div className="fixed top-4 right-4 z-[100] flex flex-col gap-2 pointer-events-none">
        {notifications.map(notif => (
          <div 
            key={notif.id}
            className={`pointer-events-auto flex items-start gap-3 p-4 rounded-lg shadow-lg border w-80 animate-in slide-in-from-right-8 fade-in duration-300 ${
              notif.type === 'success' ? 'bg-emerald-50 border-emerald-200 text-emerald-800' :
              notif.type === 'error' ? 'bg-red-50 border-red-200 text-red-800' :
              'bg-white border-slate-200 text-slate-800'
            }`}
          >
            <Bell size={18} className={`shrink-0 mt-0.5 ${notif.type === 'success' ? 'text-emerald-500' : notif.type === 'error' ? 'text-red-500' : 'text-blue-500'}`} />
            <p className="text-sm flex-1">{notif.message}</p>
            <button 
              onClick={() => removeNotification(notif.id)}
              className="text-slate-400 hover:text-slate-600 transition"
            >
              <X size={16} />
            </button>
          </div>
        ))}
      </div>
    </NotificationContext.Provider>
  );
}

export const useNotification = () => {
  const context = useContext(NotificationContext);
  if (!context) throw new Error('useNotification must be used within NotificationProvider');
  return context;
};
