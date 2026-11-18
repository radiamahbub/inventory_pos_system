import { useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import toast from 'react-hot-toast';
import { useAuth } from '@/context/AuthContext';

/** Sidebar ও Topbar — দুই জায়গা থেকেই একই logout আচরণ */
export function useLogout() {
  const { logout } = useAuth();
  const navigate = useNavigate();
  return useCallback(async () => {
    await logout();
    toast.success('Signed out successfully');
    navigate('/login', { replace: true });
  }, [logout, navigate]);
}
