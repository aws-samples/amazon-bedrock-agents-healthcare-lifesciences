import { useState } from 'react';
import Container from '@cloudscape-design/components/container';
import Header from '@cloudscape-design/components/header';
import SpaceBetween from '@cloudscape-design/components/space-between';
import FormField from '@cloudscape-design/components/form-field';
import Input from '@cloudscape-design/components/input';
import Button from '@cloudscape-design/components/button';
import Alert from '@cloudscape-design/components/alert';
import Box from '@cloudscape-design/components/box';
import { signIn, signUp, confirmSignUp, confirmSignIn } from './auth';

type AuthView = 'signIn' | 'signUp' | 'confirmSignUp' | 'newPasswordRequired';

interface Props {
  onAuthenticated: () => void;
}

export default function LoginPage({ onAuthenticated }: Props) {
  const [view, setView] = useState<AuthView>('signIn');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmCode, setConfirmCode] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSignIn = async () => {
    setError('');
    setLoading(true);
    try {
      const result = await signIn({ username: email, password });
      if (result.isSignedIn) onAuthenticated();
      else if (result.nextStep?.signInStep === 'CONFIRM_SIGN_IN_WITH_NEW_PASSWORD_REQUIRED') {
        setView('newPasswordRequired');
      } else {
        setError('Sign-in requires additional steps. Check your email.');
      }
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Sign-in failed');
    } finally {
      setLoading(false);
    }
  };

  const handleSignUp = async () => {
    setError('');
    setLoading(true);
    try {
      await signUp({ username: email, password });
      setView('confirmSignUp');
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Sign-up failed');
    } finally {
      setLoading(false);
    }
  };

  const handleNewPassword = async () => {
    setError('');
    setLoading(true);
    try {
      const result = await confirmSignIn({ challengeResponse: newPassword });
      if (result.isSignedIn) onAuthenticated();
      else setError('Unable to complete password change.');
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Password change failed');
    } finally {
      setLoading(false);
    }
  };

  const handleConfirm = async () => {
    setError('');
    setLoading(true);
    try {
      await confirmSignUp({ username: email, confirmationCode: confirmCode });
      // Auto sign-in after confirmation
      const result = await signIn({ username: email, password });
      if (result.isSignedIn) onAuthenticated();
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Confirmation failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <Box padding="xxxl">
      <div style={{ maxWidth: 420, margin: '80px auto' }}>
        <Container header={<Header variant="h1">Connected Care Platform</Header>}>
          <SpaceBetween size="l">
            {error && <Alert type="error">{error}</Alert>}

            {view === 'signIn' && (
              <SpaceBetween size="m">
                <FormField label="Email">
                  <Input type="email" value={email} onChange={({ detail }) => setEmail(detail.value)} placeholder="you@hospital.org" />
                </FormField>
                <FormField label="Password">
                  <Input type="password" value={password} onChange={({ detail }) => setPassword(detail.value)} />
                </FormField>
                <Button variant="primary" fullWidth loading={loading} onClick={handleSignIn}>Sign in</Button>
                <Box textAlign="center">
                  <Button variant="link" onClick={() => { setError(''); setView('signUp'); }}>Create an account</Button>
                </Box>
              </SpaceBetween>
            )}

            {view === 'signUp' && (
              <SpaceBetween size="m">
                <FormField label="Email">
                  <Input type="email" value={email} onChange={({ detail }) => setEmail(detail.value)} placeholder="you@hospital.org" />
                </FormField>
                <FormField label="Password" description="Min 8 chars, uppercase, lowercase, number">
                  <Input type="password" value={password} onChange={({ detail }) => setPassword(detail.value)} />
                </FormField>
                <Button variant="primary" fullWidth loading={loading} onClick={handleSignUp}>Create account</Button>
                <Box textAlign="center">
                  <Button variant="link" onClick={() => { setError(''); setView('signIn'); }}>Back to sign in</Button>
                </Box>
              </SpaceBetween>
            )}

            {view === 'confirmSignUp' && (
              <SpaceBetween size="m">
                <Alert type="info">Check your email for a verification code.</Alert>
                <FormField label="Verification code">
                  <Input value={confirmCode} onChange={({ detail }) => setConfirmCode(detail.value)} placeholder="123456" />
                </FormField>
                <Button variant="primary" fullWidth loading={loading} onClick={handleConfirm}>Verify & sign in</Button>
              </SpaceBetween>
            )}

            {view === 'newPasswordRequired' && (
              <SpaceBetween size="m">
                <Alert type="info">Your temporary password has expired. Please set a new password.</Alert>
                <FormField label="New Password" description="Min 8 chars, uppercase, lowercase, number">
                  <Input type="password" value={newPassword} onChange={({ detail }) => setNewPassword(detail.value)} />
                </FormField>
                <Button variant="primary" fullWidth loading={loading} onClick={handleNewPassword}>Set new password</Button>
              </SpaceBetween>
            )}
          </SpaceBetween>
        </Container>
      </div>
    </Box>
  );
}
