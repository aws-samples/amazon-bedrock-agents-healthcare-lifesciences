/**
 * Cognito auth module — handles sign-in, sign-up, token management,
 * and SigV4-signed requests to the IAM-authenticated Lambda Function URL.
 *
 * Uses aws-amplify v6 for Cognito auth + @aws-sdk for SigV4 signing.
 */

import { Amplify } from 'aws-amplify';
import { signIn, signUp, confirmSignUp, confirmSignIn, signOut, getCurrentUser, fetchAuthSession, fetchUserAttributes } from 'aws-amplify/auth';
import { Sha256 } from '@aws-crypto/sha256-js';
import { SignatureV4 } from '@smithy/signature-v4';
import { HttpRequest } from '@smithy/protocol-http';

// Config from environment variables (set after CDK deploy)
const REGION = import.meta.env.VITE_AWS_REGION || 'us-east-1';
const USER_POOL_ID = import.meta.env.VITE_COGNITO_USER_POOL_ID || '';
const USER_POOL_CLIENT_ID = import.meta.env.VITE_COGNITO_USER_POOL_CLIENT_ID || '';
const IDENTITY_POOL_ID = import.meta.env.VITE_COGNITO_IDENTITY_POOL_ID || '';
const FUNCTION_URL = import.meta.env.VITE_FUNCTION_URL || '';

Amplify.configure({
  Auth: {
    Cognito: {
      userPoolId: USER_POOL_ID,
      userPoolClientId: USER_POOL_CLIENT_ID,
      identityPoolId: IDENTITY_POOL_ID,
    },
  },
});

export { signIn, signUp, confirmSignUp, confirmSignIn, signOut, getCurrentUser, fetchUserAttributes };

export function getFunctionUrl(): string {
  return FUNCTION_URL;
}

/**
 * Make a SigV4-signed request to the Lambda Function URL.
 * Fetches temporary IAM credentials from Cognito Identity Pool, then signs the request.
 */
export async function signedFetch(
  path: string,
  options: { method?: string; body?: string; signal?: AbortSignal } = {},
): Promise<Response> {
  const session = await fetchAuthSession();
  const credentials = session.credentials;
  if (!credentials) throw new Error('Not authenticated — no AWS credentials');

  const url = new URL(path, FUNCTION_URL);
  const method = options.method || 'GET';

  // Extract query params for proper SigV4 signing
  const query: Record<string, string> = {};
  url.searchParams.forEach((value, key) => {
    query[key] = value;
  });

  const request = new HttpRequest({
    method,
    protocol: 'https:',
    hostname: url.hostname,
    path: url.pathname,
    query,
    headers: {
      host: url.hostname,
      'content-type': 'application/json',
    },
    body: options.body,
  });

  const signer = new SignatureV4({
    service: 'lambda',
    region: REGION,
    credentials: {
      accessKeyId: credentials.accessKeyId,
      secretAccessKey: credentials.secretAccessKey,
      sessionToken: credentials.sessionToken,
    },
    sha256: Sha256,
  });

  const signed = await signer.sign(request);

  return fetch(url.toString(), {
    method,
    headers: signed.headers as Record<string, string>,
    body: options.body,
    signal: options.signal,
  });
}
