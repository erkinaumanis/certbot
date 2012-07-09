#!/usr/bin/env python

# use OpenSSL to provide CSR-related operations

import subprocess, tempfile, re, pkcs10
# we can use tempfile.NamedTemporaryFile() to get tempfiles
# to pass to OpenSSL subprocesses.

def parse(csr):
    """Is this CSR syntactically valid?"""
    out, err = subprocess.Popen(["openssl", "req", "-noout"],shell=False,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE).communicate(csr)
    if not err:
       return True
    return False

def modulusbits(key):
    """How many bits are in the modulus of this key?"""
    out, err = subprocess.Popen(["openssl", "rsa", "-pubin", "-text", "-noout"],shell=False,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE).communicate(key)
    if out and not err:
        try:
            size = re.search("(Public-Key|Modulus):? \(([0-9]+) bit\)", out).groups()[-1]
        except:
            return None
        return int(size)
    return None

def goodkey(key):
    """Does this public key comply with our CA policy?"""
    bits = modulusbits(key)
    if bits and bits >= 2000:
        return True
    else:
        return False

def csr_goodkey(csr):
    """Does this CSR's embedded public key comply with our CA policy?"""
    if not parse(csr): return False
    key = pubkey(csr)
    return goodkey(key)

def pubkey(csr):
    """Get the public key from this CSR."""
    out, err = subprocess.Popen(["openssl", "req", "-pubkey", "-noout"],shell=False,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE).communicate(csr)
    if out and not err:
        return out
    return None

def subject(csr):
    """Get the X.509 subject from this CSR."""
    out, err = subprocess.Popen(["openssl", "req", "-subject", "-noout"],shell=False,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE).communicate(csr)
    if out and not err:
        return out
    return None

def cn(csr):
    """Get the common name from this CSR.  Requires there be exactly one."""
    cns = []
    s = subject(csr)
    if s:
       cns = [x for x in s.rstrip().split("/") if x[:3] == "CN="]
    if len(cns) == 1:
       return cns[0].split("=")[1]
    return None

def subject_names(csr):
    """Get the cn and subjectAltNames from this CSR."""
    return pkcs10.subject_names(csr)

def can_sign(name):
    """Does this CA's policy forbid signing this name via Chocolate DV?"""
    # We could have a regular expression match here, like
    # ([a-z0-9]+\.)+[a-z0-9]+
    # and there is also a list of TLDs to check against to confirm that
    # the name is actually a FQDN.
    if "." not in name: return False
    # Examples of names that are forbidden by policy due to a blacklist.
    if name in ["google.com", "www.google.com"]: return False
    return True

def verify(key, data):
    """What string was validly signed by this public key? (or None)"""
    # Note: Only relatively short strings will work, so we normally
    # sign a hash of the signed data rather than signing the signed
    # data directly.
    with tempfile.NamedTemporaryFile() as tmp:
        tmp.write(key)
        tmp.flush()
        out, err = subprocess.Popen(["openssl", "rsautl", "-pubin", "-inkey", tmp.name, "-verify"],shell=False,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE).communicate(data)
    if out and not err:
        return out
    return None

def sign(key, data):
    """Sign this data with this private key.  For client-side use."""
    with tempfile.NamedTemporaryFile() as tmp:
        tmp.write(key)
        tmp.flush()
        out, err = subprocess.Popen(["openssl", "rsautl", "-inkey", tmp.name, "-sign"],shell=False,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE).communicate(data)
    if out and not err:
        return out
    return None

def encrypt(key, data):
    """Encrypt this data with this public key."""
    with tempfile.NamedTemporaryFile() as tmp:
        tmp.write(key)
        tmp.flush()
        out, err = subprocess.Popen(["openssl", "rsautl", "-pubin", "-inkey", tmp.name, "-encrypt"],shell=False,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE).communicate(data)
    if out and not err:
        return out
    return None

def issue(csr):
    """Issue the certificate requested by this CSR and return it!"""
    # TODO: a real CA should severely restrict the content of the cert, not
    # just grant what's asked for.  (For example, the CA shouldn't trust
    # all the data in the subject field if it hasn't been validated.)
    # Therefore, we should construct a new CSR from scratch using the
    # parsed-out data from the input CSR, and then pass that to OpenSSL.
    cert = None
    with tempfile.NamedTemporaryFile() as csr_tmp:
        csr_tmp.write(csr)
        csr_tmp.flush()
        with tempfile.NamedTemporaryFile() as cert_tmp:
            ret = subprocess.Popen(["./CA.sh", "-chocolate", csr_tmp.name, cert_tmp.name],shell=False,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE).wait()
            if ret == 0:
                cert = cert_tmp.read()
    return cert
