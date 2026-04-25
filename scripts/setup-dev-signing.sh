#!/bin/bash
# One-time setup: create a self-signed code-signing certificate named
# "OpenWhisper Dev" in the user's login Keychain.
#
# After running this once, ./build-macos.sh will sign the .app with a
# stable identity. macOS TCC tracks signed apps by certificate identity
# (not cdhash), so an Accessibility grant given to one build of the app
# persists across all future rebuilds — no more drag-into-System-Settings
# dance after each build.
#
# Idempotent: re-running this is a no-op if the cert already exists.
set -euo pipefail

CERT_NAME="OpenWhisper Dev"

# Already exists? Bail.
if security find-identity -p codesigning 2>/dev/null \
    | grep -q "\"$CERT_NAME\""
then
    echo "setup-dev-signing: '$CERT_NAME' is already in your login Keychain."
    echo "Nothing to do."
    exit 0
fi

echo "Creating self-signed code-signing certificate '$CERT_NAME'…"

WORK=$(mktemp -d)
trap 'rm -rf "$WORK"' EXIT

cat >"$WORK/openssl.cnf" <<'EOF'
[req]
distinguished_name = dn
prompt             = no
[dn]
CN = OpenWhisper Dev
[v3_ext]
basicConstraints     = critical, CA:false
keyUsage             = critical, digitalSignature
extendedKeyUsage     = critical, codeSigning
subjectKeyIdentifier = hash
EOF

# 1. Generate private key + self-signed cert in one shot.
openssl req -x509 -newkey rsa:2048 -nodes \
    -keyout "$WORK/key.pem" \
    -out    "$WORK/cert.pem" \
    -days   3650 \
    -config "$WORK/openssl.cnf" \
    -extensions v3_ext \
    >/dev/null 2>&1

# 2. Bundle key + cert into a PKCS#12 archive (security import wants this).
P12_PASS="openwhisper-dev-$$"
openssl pkcs12 -export \
    -inkey "$WORK/key.pem" \
    -in    "$WORK/cert.pem" \
    -name  "$CERT_NAME" \
    -out   "$WORK/cert.p12" \
    -password "pass:$P12_PASS" \
    >/dev/null 2>&1

# 3. Import into the login keychain. -T whitelists codesign to use the
#    private key without an ACL prompt.
security import "$WORK/cert.p12" \
    -P "$P12_PASS" \
    -T /usr/bin/codesign \
    >/dev/null

cat <<EOF

✓ Created '$CERT_NAME' in your login Keychain.

What happens next:
  • The first time you run ./build-macos.sh, the build will sign the app
    with this certificate.
  • The first time codesign uses this key, macOS may show a dialog asking
    permission. Click "Always Allow" — you only see it once.
  • After your initial Accessibility grant for the new build, every
    subsequent rebuild keeps the grant. No more drag-and-drop dance.

To remove this certificate later:
  security delete-certificate -c "$CERT_NAME" login.keychain-db
EOF
