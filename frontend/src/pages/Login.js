import React, { useState } from 'react';
import { Link, useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { Input } from '../components/ui/input';
import { Button } from '../components/ui/button';

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
