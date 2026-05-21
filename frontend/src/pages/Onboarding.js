import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { Input } from '../components/ui/input';
import { Button } from '../components/ui/button';
import { toast } from 'sonner';
import axios from 'axios';

const API = process.env.REACT_APP_BACKEND_URL + '/api';

export function Onboarding() {
  const [step, setStep] = useState(1);
  const [loading, setLoading] = useState(false);
  const { user, updateProfile, completeOnboarding } = useAuth();
  const navigate = useNavigate();

  // Step 1: Profile
  const [profile, setProfile] = useState({
    fca_number: ''
  });

  // Step 2: Lender
  const [lender, setLender] = useState({
    name: '',
    bdm_name: '',
    bdm_email: '',
    bdm_phone: ''
  });

  // Step 3: Client
  const [client, setClient] = useState({
    first_name: '',
    last_name: '',
    email: '',
    phone: ''
  });

  const handleProfileSubmit = async () => {
    setLoading(true);
    const result = await updateProfile({ fca_number: profile.fca_number });
    setLoading(false);
    if (result.success) {
      setStep(2);
    } else {
      toast.error(result.error);
    }
  };

  const handleLenderSubmit = async () => {
    if (!lender.name) {
      setStep(3);
      return;
    }
    setLoading(true);
    try {
      await axios.post(`${API}/lenders`, lender, { withCredentials: true });
      setStep(3);
    } catch (error) {
      toast.error('Failed to add lender');
    }
    setLoading(false);
  };

  const handleClientSubmit = async () => {
    if (!client.first_name || !client.last_name) {
      await finishOnboarding();
      return;
    }
    setLoading(true);
    try {
      await axios.post(`${API}/clients`, client, { withCredentials: true });
      await finishOnboarding();
    } catch (error) {
      toast.error('Failed to add client');
    }
    setLoading(false);
  };

  const finishOnboarding = async () => {
    await completeOnboarding();
    toast.success('Welcome to BrokerOS!');
    navigate('/dashboard');
  };

  const handleSkip = () => {
    if (step === 1) setStep(2);
    else if (step === 2) setStep(3);
    else finishOnboarding();
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-[#F8F9FA] p-4">
      <div className="w-full max-w-lg">
        <div className="bg-white border border-[#E5E7EB] rounded-lg p-8">
          <div className="text-center mb-8">
            <h1 className="text-[#0A2342] text-xl font-bold">BrokerOS</h1>
            <p className="text-[#93C5FD] text-xs mt-1">Practice Management</p>
          </div>

          {/* Progress indicator */}
          <div className="flex items-center justify-center gap-2 mb-8">
            {[1, 2, 3].map((s) => (
              <div
                key={s}
                className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-medium ${
                  s === step
                    ? 'bg-[#0E9F6E] text-white'
                    : s < step
                    ? 'bg-[#D1FAE5] text-[#065F46]'
                    : 'bg-[#F3F4F6] text-[#6B7280]'
                }`}
              >
                {s}
              </div>
            ))}
          </div>

          {/* Step 1: Profile */}
          {step === 1 && (
            <div data-testid="onboarding-step-1">
              <h2 className="text-lg font-semibold text-[#111827] mb-2">Complete your profile</h2>
              <p className="text-sm text-[#6B7280] mb-6">
                Add your FCA number so clients and lenders can verify your credentials.
              </p>

              <div className="space-y-5">
                <div>
                  <label className="form-label">FCA Number</label>
                  <Input
                    type="text"
                    value={profile.fca_number}
                    onChange={(e) => setProfile({ ...profile, fca_number: e.target.value })}
                    placeholder="e.g. 123456"
                    className="form-input"
                    data-testid="fca-number-input"
                  />
                </div>

                <div className="flex gap-3">
                  <Button
                    type="button"
                    onClick={handleSkip}
                    variant="outline"
                    className="flex-1 border-[#E5E7EB]"
                    data-testid="skip-btn"
                  >
                    Skip
                  </Button>
                  <Button
                    type="button"
                    onClick={handleProfileSubmit}
                    disabled={loading}
                    className="flex-1 bg-[#0E9F6E] hover:bg-[#0d8a5f] text-white"
                    data-testid="continue-btn"
                  >
                    {loading ? 'Saving...' : 'Continue'}
                  </Button>
                </div>
              </div>
            </div>
          )}

          {/* Step 2: Lender */}
          {step === 2 && (
            <div data-testid="onboarding-step-2">
              <h2 className="text-lg font-semibold text-[#111827] mb-2">Add your first lender</h2>
              <p className="text-sm text-[#6B7280] mb-6">
                Add a lender to your panel. You can add more later.
              </p>

              <div className="space-y-5">
                <div>
                  <label className="form-label">Lender name</label>
                  <Input
                    type="text"
                    value={lender.name}
                    onChange={(e) => setLender({ ...lender, name: e.target.value })}
                    placeholder="e.g. Nationwide"
                    className="form-input"
                    data-testid="lender-name-input"
                  />
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="form-label">BDM name</label>
                    <Input
                      type="text"
                      value={lender.bdm_name}
                      onChange={(e) => setLender({ ...lender, bdm_name: e.target.value })}
                      placeholder="Contact name"
                      className="form-input"
                      data-testid="bdm-name-input"
                    />
                  </div>
                  <div>
                    <label className="form-label">BDM email</label>
                    <Input
                      type="email"
                      value={lender.bdm_email}
                      onChange={(e) => setLender({ ...lender, bdm_email: e.target.value })}
                      placeholder="bdm@lender.com"
                      className="form-input"
                      data-testid="bdm-email-input"
                    />
                  </div>
                </div>

                <div className="flex gap-3">
                  <Button
                    type="button"
                    onClick={handleSkip}
                    variant="outline"
                    className="flex-1 border-[#E5E7EB]"
                    data-testid="skip-btn"
                  >
                    Skip
                  </Button>
                  <Button
                    type="button"
                    onClick={handleLenderSubmit}
                    disabled={loading}
                    className="flex-1 bg-[#0E9F6E] hover:bg-[#0d8a5f] text-white"
                    data-testid="continue-btn"
                  >
                    {loading ? 'Saving...' : 'Continue'}
                  </Button>
                </div>
              </div>
            </div>
          )}

          {/* Step 3: Client */}
          {step === 3 && (
            <div data-testid="onboarding-step-3">
              <h2 className="text-lg font-semibold text-[#111827] mb-2">Add your first client</h2>
              <p className="text-sm text-[#6B7280] mb-6">
                Add a client to get started. You can add more details later.
              </p>

              <div className="space-y-5">
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="form-label">First name</label>
                    <Input
                      type="text"
                      value={client.first_name}
                      onChange={(e) => setClient({ ...client, first_name: e.target.value })}
                      placeholder="John"
                      className="form-input"
                      data-testid="client-first-name-input"
                    />
                  </div>
                  <div>
                    <label className="form-label">Last name</label>
                    <Input
                      type="text"
                      value={client.last_name}
                      onChange={(e) => setClient({ ...client, last_name: e.target.value })}
                      placeholder="Smith"
                      className="form-input"
                      data-testid="client-last-name-input"
                    />
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="form-label">Email</label>
                    <Input
                      type="email"
                      value={client.email}
                      onChange={(e) => setClient({ ...client, email: e.target.value })}
                      placeholder="client@email.com"
                      className="form-input"
                      data-testid="client-email-input"
                    />
                  </div>
                  <div>
                    <label className="form-label">Phone</label>
                    <Input
                      type="tel"
                      value={client.phone}
                      onChange={(e) => setClient({ ...client, phone: e.target.value })}
                      placeholder="07123 456789"
                      className="form-input"
                      data-testid="client-phone-input"
                    />
                  </div>
                </div>

                <div className="flex gap-3">
                  <Button
                    type="button"
                    onClick={handleSkip}
                    variant="outline"
                    className="flex-1 border-[#E5E7EB]"
                    data-testid="skip-btn"
                  >
                    Skip
                  </Button>
                  <Button
                    type="button"
                    onClick={handleClientSubmit}
                    disabled={loading}
                    className="flex-1 bg-[#0E9F6E] hover:bg-[#0d8a5f] text-white"
                    data-testid="finish-btn"
                  >
                    {loading ? 'Finishing...' : 'Finish setup'}
                  </Button>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
