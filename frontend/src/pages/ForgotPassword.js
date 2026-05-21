import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { Input } from '../components/ui/input';
import { Button } from '../components/ui/button';

export function ForgotPassword() {
  const [email, setEmail] = useState('');
  const [error, setError] = useState('');
  const [success, setSuccess] = useState(false);
  const [loading, setLoading] = useState(false);
  const { forgotPassword } = useAuth();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    const result = await forgotPassword(email);
    setLoading(false);

    if (result.success) {
      setSuccess(true);
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

          <h2 className="text-lg font-semibold text-[#111827] mb-2">Reset your password</h2>
          <p className="text-sm text-[#6B7280] mb-6">
            Enter your email address and we'll send you a link to reset your password.
          </p>

          {success ? (
            <div className="text-center">
              <div className="bg-[#D1FAE5] text-[#065F46] text-sm p-4 rounded-md mb-6">
                If an account with that email exists, we've sent a password reset link.
              </div>
              <Link
                to="/login"
                className="text-[#0E9F6E] hover:underline font-medium text-sm"
                data-testid="back-to-login-link"
              >
                Back to sign in
              </Link>
            </div>
          ) : (
            <>
              {error && (
                <div className="bg-[#FEE2E2] text-[#DC2626] text-sm p-3 rounded-md mb-4" data-testid="forgot-password-error">
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

                <Button
                  type="submit"
                  disabled={loading}
                  className="w-full bg-[#0E9F6E] hover:bg-[#0d8a5f] text-white rounded-lg py-3"
                  data-testid="reset-submit-btn"
                >
                  {loading ? 'Sending...' : 'Send reset link'}
                </Button>
              </form>

              <p className="mt-6 text-center text-sm text-[#6B7280]">
                Remember your password?{' '}
                <Link
                  to="/login"
                  className="text-[#0E9F6E] hover:underline font-medium"
                  data-testid="login-link"
                >
                  Sign in
                </Link>
              </p>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
