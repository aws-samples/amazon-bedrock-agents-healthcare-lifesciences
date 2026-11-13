/*
 * auth.js — Amazon Cognito Hosted UI login (OAuth2 Authorization Code + PKCE).
 *
 * Access to the app is restricted to users provisioned in the Cognito user pool
 * (self sign-up is disabled). On load, the page redirects to the Hosted UI if
 * there is no valid session. All calls to the application API automatically
 * carry the Cognito ID token; calls to other origins (e.g. presigned S3 URLs)
 * are left untouched.
 *
 * Exposes:
 *   window.__authReady  — a promise that resolves once a valid session exists
 *   window.signOut()    — clears the session and returns to the Hosted UI
 */
(function () {
  "use strict";

  if (typeof COGNITO === "undefined" || !COGNITO.domain || !COGNITO.clientId) {
    console.error("Cognito config missing (config.js); authentication is disabled.");
    window.__authReady = Promise.resolve(false);
    return;
  }

  var KEY = {
    id: "pl_id_token",
    access: "pl_access_token",
    refresh: "pl_refresh_token",
    exp: "pl_token_exp",
    verifier: "pl_pkce_verifier",
  };
  // redirect_uri must match a callback URL registered on the app client.
  var redirectUri = window.location.origin + window.location.pathname;

  function b64url(buffer) {
    var bytes = new Uint8Array(buffer);
    var str = "";
    for (var i = 0; i < bytes.length; i++) str += String.fromCharCode(bytes[i]);
    return btoa(str).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
  }

  function randomString(byteLen) {
    var arr = new Uint8Array(byteLen);
    crypto.getRandomValues(arr);
    var out = "";
    for (var i = 0; i < arr.length; i++) out += ("0" + arr[i].toString(16)).slice(-2);
    return out;
  }

  async function sha256(str) {
    return crypto.subtle.digest("SHA-256", new TextEncoder().encode(str));
  }

  function getIdToken() {
    return sessionStorage.getItem(KEY.id);
  }

  function isExpired() {
    var exp = parseInt(sessionStorage.getItem(KEY.exp) || "0", 10);
    return Date.now() >= exp - 60000; // treat as expired 1 minute early
  }

  function storeTokens(t, fallbackRefresh) {
    if (t.id_token) sessionStorage.setItem(KEY.id, t.id_token);
    if (t.access_token) sessionStorage.setItem(KEY.access, t.access_token);
    if (t.refresh_token) sessionStorage.setItem(KEY.refresh, t.refresh_token);
    else if (fallbackRefresh) sessionStorage.setItem(KEY.refresh, fallbackRefresh);
    var ttl = (t.expires_in || 3600) * 1000;
    sessionStorage.setItem(KEY.exp, String(Date.now() + ttl));
  }

  async function login() {
    var verifier = randomString(48);
    sessionStorage.setItem(KEY.verifier, verifier);
    var challenge = b64url(await sha256(verifier));
    var params = new URLSearchParams({
      response_type: "code",
      client_id: COGNITO.clientId,
      redirect_uri: redirectUri,
      scope: "openid email profile",
      code_challenge_method: "S256",
      code_challenge: challenge,
    });
    window.location.assign(COGNITO.domain + "/oauth2/authorize?" + params.toString());
  }

  function signOut() {
    Object.keys(KEY).forEach(function (k) { sessionStorage.removeItem(KEY[k]); });
    var params = new URLSearchParams({
      client_id: COGNITO.clientId,
      logout_uri: redirectUri,
    });
    window.location.assign(COGNITO.domain + "/logout?" + params.toString());
  }
  window.signOut = signOut;

  async function exchangeCode(code) {
    var verifier = sessionStorage.getItem(KEY.verifier);
    var body = new URLSearchParams({
      grant_type: "authorization_code",
      client_id: COGNITO.clientId,
      code: code,
      redirect_uri: redirectUri,
      code_verifier: verifier || "",
    });
    var resp = await originalFetch(COGNITO.domain + "/oauth2/token", {
      method: "POST",
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
      body: body.toString(),
    });
    if (!resp.ok) throw new Error("Token exchange failed: " + resp.status);
    return resp.json();
  }

  async function refresh() {
    var rt = sessionStorage.getItem(KEY.refresh);
    if (!rt) return false;
    var body = new URLSearchParams({
      grant_type: "refresh_token",
      client_id: COGNITO.clientId,
      refresh_token: rt,
    });
    var resp = await originalFetch(COGNITO.domain + "/oauth2/token", {
      method: "POST",
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
      body: body.toString(),
    });
    if (!resp.ok) return false;
    storeTokens(await resp.json(), rt);
    return true;
  }

  // Wrap fetch so application API calls carry the bearer token. Requests to any
  // other origin (presigned S3 URLs, Cognito token endpoint) are untouched.
  var originalFetch = window.fetch.bind(window);
  window.fetch = async function (input, init) {
    init = init || {};
    var url = typeof input === "string" ? input : (input && input.url) || "";
    if (typeof API_ENDPOINT !== "undefined" && API_ENDPOINT && url.indexOf(API_ENDPOINT) === 0) {
      if (isExpired()) await refresh();
      var token = getIdToken();
      var headers = Object.assign({}, init.headers || {}, { Authorization: "Bearer " + token });
      init = Object.assign({}, init, { headers: headers });
    }
    return originalFetch(input, init);
  };

  async function ensureAuth() {
    var url = new URL(window.location.href);
    var code = url.searchParams.get("code");
    if (code) {
      try {
        storeTokens(await exchangeCode(code));
        sessionStorage.removeItem(KEY.verifier);
      } catch (e) {
        console.error(e);
      }
      url.searchParams.delete("code");
      url.searchParams.delete("state");
      window.history.replaceState({}, document.title, url.pathname + url.search + url.hash);
    }
    if (!getIdToken()) {
      await login();
      return false;
    }
    if (isExpired()) {
      var ok = await refresh();
      if (!ok) {
        await login();
        return false;
      }
    }
    return true;
  }

  window.__authReady = ensureAuth();
})();
