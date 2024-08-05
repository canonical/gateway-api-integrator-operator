<!-- markdownlint-disable -->

<a href="../src/tls_relation.py#L0"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

# <kbd>module</kbd> `tls_relation.py`
Gateway API TLS relation business logic. 

**Global Variables**
---------------
- **TLS_CERT**

---

<a href="../src/tls_relation.py#L43"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

## <kbd>function</kbd> `get_hostname_from_cert`

```python
get_hostname_from_cert(certificate: str) → str
```

Get the hostname from a certificate subject name. 



**Args:**
 
 - <b>`certificate`</b>:  The certificate in PEM format. 



**Returns:**
 The hostname the certificate is issue to. 



**Raises:**
 
 - <b>`InvalidCertificateError`</b>:  When hostname cannot be parsed from the given certificate. 


---

## <kbd>class</kbd> `InvalidCertificateError`
Exception raised when certificates is invalid. 





---

## <kbd>class</kbd> `KeyPair`
Stores a private key and encryption password. 



**Attributes:**
 
 - <b>`private_key`</b>:  The private key 
 - <b>`password`</b>:  The password used for encryption 





---

## <kbd>class</kbd> `TLSRelationService`
TLS Relation service class. 

<a href="../src/tls_relation.py#L69"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

### <kbd>function</kbd> `__init__`

```python
__init__(model: Model, certificates: TLSCertificatesRequiresV3) → None
```

Init method for the class. 



**Args:**
 
 - <b>`model`</b>:  The charm's current model. 
 - <b>`certificates`</b>:  The TLS certificates requirer library. 




---

<a href="../src/tls_relation.py#L136"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

### <kbd>function</kbd> `certificate_expiring`

```python
certificate_expiring(event: CertificateExpiringEvent) → None
```

Handle the TLS Certificate expiring event. 



**Args:**
 
 - <b>`event`</b>:  The event that fires this method. 

---

<a href="../src/tls_relation.py#L160"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

### <kbd>function</kbd> `certificate_invalidated`

```python
certificate_invalidated(event: CertificateInvalidatedEvent) → None
```

Handle TLS Certificate revocation. 



**Args:**
 
 - <b>`event`</b>:  The event that fires this method. 

---

<a href="../src/tls_relation.py#L81"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

### <kbd>function</kbd> `generate_password`

```python
generate_password() → str
```

Generate a random 12 character password. 



**Returns:**
 
 - <b>`str`</b>:  Private key string. 

---

<a href="../src/tls_relation.py#L105"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

### <kbd>function</kbd> `generate_private_key`

```python
generate_private_key(hostname: str) → None
```

Handle the TLS Certificate created event. 



**Args:**
 
 - <b>`hostname`</b>:  Certificate's hostname. 



**Raises:**
 
 - <b>`AssertionError`</b>:  If this method is called before the certificates integration is ready. 

---

<a href="../src/tls_relation.py#L90"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

### <kbd>function</kbd> `request_certificate`

```python
request_certificate(hostname: str) → None
```

Handle the TLS Certificate joined event. 



**Args:**
 
 - <b>`hostname`</b>:  Certificate's hostname. 

---

<a href="../src/tls_relation.py#L177"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

### <kbd>function</kbd> `revoke_all_certificates`

```python
revoke_all_certificates() → None
```

Revoke all provider certificates and remove all revisions in juju secret. 


