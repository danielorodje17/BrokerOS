import React, { useState } from 'react';
import { useAuth } from '../contexts/AuthContext';
import { toast } from 'sonner';
import { Input } from '../components/ui/input';
import { Button } from '../components/ui/button';

export function Settings() {
  const { user, updateProfile } = useAuth();
  const [loading, setLoading] = useState(false);
  const [formData, setFormData] = useState({
    first_name: user?.first_name || '',
    last_name: user?.last_name || '',
    fca_number: user?.fca_number || '',
    current_password: '',
    new_password: '',
    confirm_password: ''
  });

  const handleProfileSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);

    const result = await updateProfile({
      first_name: formData.first_name,
      last_name: formData.last_name,
      fca_number: formData.fca_number
    });

    setLoading(false);
    if (result.success) {
      toast.success('Profile updated');
    } else {
      toast.error(result.error);
    }
  };

  const handlePasswordSubmit = async (e) => {
    e.preventDefault();

    if (formData.new_password !== formData.confirm_password) {
      toast.error('Passwords do not match');
      return;
    }

    if (formData.new_password.length < 6) {
      toast.error('Password must be at least 6 characters');
      return;
    }

    setLoading(true);

    const result = await updateProfile({
      current_password: formData.current_password,
      new_password: formData.new_password
    });

    setLoading(false);
    if (result.success) {
      toast.success('Password updated');
      setFormData(prev => ({
        ...prev,
        current_password: '',
        new_password: '',
        confirm_password: ''
      }));
    } else {
      toast.error(result.error);
    }
  };

  return (
    <div data-testid="settings-page">
      <div className="page-header">
        <h1>Settings</h1>
      </div>

      <div className="max-w-2xl space-y-6">
        {/* Profile Section */}
        <div className="card">
          <h2 className="text-lg font-semibold text-[#111827] mb-6">Profile Information</h2>
          <form onSubmit={handleProfileSubmit} className="space-y-5">
            <div className="form-grid">
              <div>
                <label className="form-label">First name</label>
                <Input
                  type="text"
                  value={formData.first_name}
                  onChange={(e) => setFormData({ ...formData, first_name: e.target.value })}
                  className="form-input"
                  data-testid="settings-first-name-input"
                />
              </div>
              <div>
                <label className="form-label">Last name</label>
                <Input
                  type="text"
                  value={formData.last_name}
                  onChange={(e) => setFormData({ ...formData, last_name: e.target.value })}
                  className="form-input"
                  data-testid="settings-last-name-input"
                />
              </div>
            </div>

            <div>
              <label className="form-label">Email address</label>
              <Input
                type="email"
                value={user?.email || ''}
                disabled
                className="form-input bg-[#F9FAFB] cursor-not-allowed"
                data-testid="settings-email-input"
              />
              <p className="text-xs text-[#6B7280] mt-1">Email cannot be changed</p>
            </div>

            <div>
              <label className="form-label">FCA Number</label>
              <Input
                type="text"
                value={formData.fca_number}
                onChange={(e) => setFormData({ ...formData, fca_number: e.target.value })}
                placeholder="e.g. 123456"
                className="form-input max-w-xs"
                data-testid="settings-fca-input"
              />
            </div>

            <div className="pt-2">
              <Button
                type="submit"
                disabled={loading}
                className="bg-[#0E9F6E] hover:bg-[#0d8a5f] text-white"
                data-testid="save-profile-btn"
              >
                {loading ? 'Saving...' : 'Save Changes'}
              </Button>
            </div>
          </form>
        </div>

        {/* Password Section */}
        <div className="card">
          <h2 className="text-lg font-semibold text-[#111827] mb-6">Change Password</h2>
          <form onSubmit={handlePasswordSubmit} className="space-y-5">
            <div>
              <label className="form-label">Current password</label>
              <Input
                type="password"
                value={formData.current_password}
                onChange={(e) => setFormData({ ...formData, current_password: e.target.value })}
                className="form-input max-w-sm"
                data-testid="current-password-input"
              />
            </div>

            <div className="form-grid max-w-lg">
              <div>
                <label className="form-label">New password</label>
                <Input
                  type="password"
                  value={formData.new_password}
                  onChange={(e) => setFormData({ ...formData, new_password: e.target.value })}
                  className="form-input"
                  data-testid="new-password-input"
                />
              </div>
              <div>
                <label className="form-label">Confirm new password</label>
                <Input
                  type="password"
                  value={formData.confirm_password}
                  onChange={(e) => setFormData({ ...formData, confirm_password: e.target.value })}
                  className="form-input"
                  data-testid="confirm-new-password-input"
                />
              </div>
            </div>

            <div className="pt-2">
              <Button
                type="submit"
                disabled={loading || !formData.current_password || !formData.new_password}
                className="bg-[#0E9F6E] hover:bg-[#0d8a5f] text-white"
                data-testid="change-password-btn"
              >
                {loading ? 'Updating...' : 'Change Password'}
              </Button>
            </div>
          </form>
        </div>

        {/* Account Info */}
        <div className="card">
          <h2 className="text-lg font-semibold text-[#111827] mb-4">Account Information</h2>
          <div className="space-y-3 text-sm">
            <div className="flex justify-between">
              <span className="text-[#6B7280]">Account type</span>
              <span className="text-[#111827] font-medium capitalize">{user?.role || 'Adviser'}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-[#6B7280]">Member since</span>
              <span className="text-[#111827]">
                {user?.created_at ? new Date(user.created_at).toLocaleDateString('en-GB') : '-'}
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
