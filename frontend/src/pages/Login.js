import React, { useState } from 'react';
import { Link, useNavigate, useLocation } from 'react-router-dom';
import axios from 'axios';
import { toast } from 'sonner';
import { useAuth } from '../contexts/AuthContext';
import { Input } from '../components/ui/input';
import { Button } from '../components/ui/button';

const API = process.env.REACT_APP_BACKEND_URL + '/api';

export function Login() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const { login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  const from = location.state?.from?.pathname || '/dashboard';

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    const result = await login(email, password);
    setLoading(false);

    if (result.success) {
      navigate(from, { replace: true });
      // Background: fire reminders check — must not block navigation
      axios.get(`${API}/commissions/reminders`, { withCredentials: true })
        .then(({ data }) => {
          const reminders = data.data;
          const overdueCount = reminders?.overdue?.length ?? 0;
          const dueSoonCount = reminders?.due_soon?.length ?? 0;
          if (overdueCount === 0 && dueSoonCount === 0) return;

          let message;
          if (overdueCount > 0 && dueSoonCount > 0) {
            message = `💰 ${overdueCount} commission(s) overdue · ${dueSoonCount} due this week — check Commission Tracker`;
          } else if (overdueCount > 0) {
            message = `⚠️ ${overdueCount} commission(s) overdue — check Commission Tracker`;
          } else {
            message = `📅 ${dueSoonCount} commission(s) due this week — check Commission Tracker`;
          }

          toast.custom(
            (t) => (
              <div
                role="button"
                tabIndex={0}
                onClick={() => { toast.dismiss(t); navigate('/commissions'); }}
                onKeyDown={(e) => e.key === 'Enter' && navigate('/commissions')}
                style={{
                  cursor: 'pointer',
                  background: '#0A2342',
                  color: 'white',
                  padding: '12px 16px',
                  borderRadius: '8px',
                  borderLeft: '4px solid #0E9F6E',
                  fontSize: '14px',
                  lineHeight: '1.5',
                  boxShadow: '0 4px 12px rgba(0,0,0,0.2)',
                  minWidth: '300px',
                  maxWidth: '420px',
                }}
                data-testid="commission-reminder-toast"
              >
                {message}
              </div>
            ),
            { duration: 6000, position: 'top-right' }
          );
        })
        .catch(() => {}); // Silently fail — reminders are non-critical
    } else {
      setError(result.error);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-[#F8F9FA] p-4">
      <div className="w-full max-w-md">
        <div className="bg-white border border-[#E5E7EB] rounded-lg p-8">
          <div className="text-center mb-8">
            <h1 className="text-[#0A2342] text-xl font-bold">BrokerOS</h1>
            <p className="text-[#93C5FD] text-xs mt-1">Practice Management</p>
          </div>

          <h2 className="text-lg font-semibold text-[#111827] mb-6">Sign in to your account</h2>

          {error && (
            <div className="bg-[#FEE2E2] text-[#DC2626] text-sm p-3 rounded-md mb-4" data-testid="login-error">
              {error}
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-5">
            <div>
              <label className="form-label">
                Email address <span className="text-[#0E9F6E]">*</span>
              </label>
              <Input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="you@example.com"
                required
                className="form-input"
                data-testid="email-input"
              />
            </div>

            <div>
              <label className="form-label">
                Password <span className="text-[#0E9F6E]">*</span>
              </label>
              <Input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="Enter your password"
                required
                className="form-input"
                data-testid="password-input"
              />
            </div>

            <div className="flex justify-end">
              <Link
                to="/forgot-password"
                className="text-sm text-[#0E9F6E] hover:underline"
                data-testid="forgot-password-link"
              >
                Forgot password?
              </Link>
            </div>

            <Button
              type="submit"
              disabled={loading}
              className="w-full bg-[#0E9F6E] hover:bg-[#0d8a5f] text-white rounded-lg py-3"
              data-testid="login-submit-btn"
            >
              {loading ? 'Signing in...' : 'Sign in'}
            </Button>
          </form>

          <p className="mt-6 text-center text-sm text-[#6B7280]">
            Don't have an account?{' '}
            <Link
              to="/register"
              className="text-[#0E9F6E] hover:underline font-medium"
              data-testid="register-link"
            >
              Create account
            </Link>
          </p>
        </div>
      </div>
    </div>
  );
}
