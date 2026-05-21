import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { Input } from '../components/ui/input';
import { Button } from '../components/ui/button';

export function Register() {
  const [formData, setFormData] = useState({
    first_name: '',
    last_name: '',
    email: '',
    password: '',
    confirm_password: ''
  });
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const { register } = useAuth();
  const navigate = useNavigate();

  const handleChange = (e) => {
    setFormData({ ...formData, [e.target.name]: e.target.value });
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');

    if (formData.password !== formData.confirm_password) {
      setError('Passwords do not match');
      return;
    }

    if (formData.password.length < 6) {
      setError('Password must be at least 6 characters');
      return;
    }

    setLoading(true);
    const result = await register(formData.email, formData.password, formData.first_name, formData.last_name);
    setLoading(false);

    if (result.success) {
      navigate('/onboarding');
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

          <h2 className="text-lg font-semibold text-[#111827] mb-6">Create your account</h2>

          {error && (
            <div className="bg-[#FEE2E2] text-[#DC2626] text-sm p-3 rounded-md mb-4" data-testid="register-error">
              {error}
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-5">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="form-label">
                  First name <span className="text-[#0E9F6E]">*</span>
                </label>
                <Input
                  type="text"
                  name="first_name"
                  value={formData.first_name}
                  onChange={handleChange}
                  placeholder="John"
                  required
                  className="form-input"
                  data-testid="first-name-input"
                />
              </div>
              <div>
                <label className="form-label">
                  Last name <span className="text-[#0E9F6E]">*</span>
                </label>
                <Input
                  type="text"
                  name="last_name"
                  value={formData.last_name}
                  onChange={handleChange}
                  placeholder="Smith"
                  required
                  className="form-input"
                  data-testid="last-name-input"
                />
              </div>
            </div>

            <div>
              <label className="form-label">
                Email address <span className="text-[#0E9F6E]">*</span>
              </label>
              <Input
                type="email"
                name="email"
                value={formData.email}
                onChange={handleChange}
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
                name="password"
                value={formData.password}
                onChange={handleChange}
                placeholder="At least 6 characters"
                required
                className="form-input"
                data-testid="password-input"
              />
            </div>

            <div>
              <label className="form-label">
                Confirm password <span className="text-[#0E9F6E]">*</span>
              </label>
              <Input
                type="password"
                name="confirm_password"
                value={formData.confirm_password}
                onChange={handleChange}
                placeholder="Confirm your password"
                required
                className="form-input"
                data-testid="confirm-password-input"
              />
            </div>

            <Button
              type="submit"
              disabled={loading}
              className="w-full bg-[#0E9F6E] hover:bg-[#0d8a5f] text-white rounded-lg py-3"
              data-testid="register-submit-btn"
            >
              {loading ? 'Creating account...' : 'Create account'}
            </Button>
          </form>

          <p className="mt-6 text-center text-sm text-[#6B7280]">
            Already have an account?{' '}
            <Link
              to="/login"
              className="text-[#0E9F6E] hover:underline font-medium"
              data-testid="login-link"
            >
              Sign in
            </Link>
          </p>
        </div>
      </div>
    </div>
  );
}
