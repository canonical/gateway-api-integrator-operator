<!-- markdownlint-disable -->

<a href="../src/tls_relation.py#L0"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

# <kbd>module</kbd> `tls_relation.py`
Gateway API TLS relation business logic. 

**Global Variables**
---------------
- **TLS_CERT**


---

## <kbd>class</kbd> `TLSRelationService`
TLS Relation service class. 

<a href="../src/tls_relation.py#L31"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

### <kbd>function</kbd> `__init__`

```python
__init__(model: Model) → None
```

Init method for the class. 



**Args:**
 
 - <b>`model`</b>:  The charm model used to get the relations and secrets. 




---

<a href="../src/tls_relation.py#L242"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

### <kbd>function</kbd> `certificate_expiring`

```python
certificate_expiring(
    event: Union[CertificateExpiringEvent, CertificateInvalidatedEvent],
    certificates: TLSCertificatesRequiresV3
) → None
```

Handle the TLS Certificate expiring event. 



**Args:**
 
 - <b>`event`</b>:  The event that fires this method. 
 - <b>`certificates`</b>:  The certificate requirer library instance. 

---

<a href="../src/tls_relation.py#L218"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

### <kbd>function</kbd> `certificate_relation_available`

```python
certificate_relation_available(event: CertificateAvailableEvent) → None
```

Handle the TLS Certificate available event. 



**Args:**
 
 - <b>`event`</b>:  The event that fires this method. 

---

<a href="../src/tls_relation.py#L191"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

### <kbd>function</kbd> `certificate_relation_created`

```python
certificate_relation_created(hostname: str) → None
```

Handle the TLS Certificate created event. 



**Args:**
 
 - <b>`hostname`</b>:  Certificate's hostname. 

---

<a href="../src/tls_relation.py#L166"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

### <kbd>function</kbd> `certificate_relation_joined`

```python
certificate_relation_joined(
    hostname: str,
    certificates: TLSCertificatesRequiresV3
) → None
```

Handle the TLS Certificate joined event. 



**Args:**
 
 - <b>`hostname`</b>:  Certificate's hostname. 
 - <b>`certificates`</b>:  The certificate requirer library instance. 

---

<a href="../src/tls_relation.py#L54"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

### <kbd>function</kbd> `generate_password`

```python
generate_password() → str
```

Generate a random 12 character password. 



**Returns:**
 
 - <b>`str`</b>:  Private key string. 

---

<a href="../src/tls_relation.py#L272"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

### <kbd>function</kbd> `get_decrypted_keys`

```python
get_decrypted_keys() → Dict[str, str]
```

Return the list of decrypted private keys. 



**Returns:**
  A dictionary indexed by domain, containing the decrypted private keys. 

---

<a href="../src/tls_relation.py#L139"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

### <kbd>function</kbd> `get_hostname_from_cert`

```python
get_hostname_from_cert(certificate: str) → str
```

Get the hostname from a certificate subject name. 



**Args:**
 
 - <b>`certificate`</b>:  The certificate in PEM format. 



**Returns:**
 The hostname the certificate is issue to. 

---

<a href="../src/tls_relation.py#L120"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

### <kbd>function</kbd> `get_relation_data_field`

```python
get_relation_data_field(relation_field: str, tls_relation: Relation) → str
```

Get an item from the app relation databag. 



**Args:**
 
 - <b>`relation_field`</b>:  item to get 
 - <b>`tls_relation`</b>:  TLS certificates relation 



**Returns:**
 The value from the field. 



**Raises:**
 
 - <b>`KeyError`</b>:  if the field is not found in the relation databag. 

---

<a href="../src/tls_relation.py#L156"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

### <kbd>function</kbd> `get_tls_relation`

```python
get_tls_relation() → Optional[Relation]
```

Get the TLS certificates relation. 



**Returns:**
  The TLS certificates relation of the charm. 

---

<a href="../src/tls_relation.py#L106"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

### <kbd>function</kbd> `pop_relation_data_fields`

```python
pop_relation_data_fields(relation_fields: list, tls_relation: Relation) → None
```

Pop a list of items from the app relation databag. 



**Args:**
 
 - <b>`relation_fields`</b>:  items to pop 
 - <b>`tls_relation`</b>:  TLS certificates relation 

---

<a href="../src/tls_relation.py#L63"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

### <kbd>function</kbd> `update_cert_on_service_hostname_change`

```python
update_cert_on_service_hostname_change(
    hostnames: List[str],
    tls_certificates_relation: Optional[Relation],
    namespace: str
) → List[str]
```

Handle TLS certificate updates when the charm config changes. 



**Args:**
 
 - <b>`hostnames`</b>:  Ingress service hostname list. 
 - <b>`tls_certificates_relation`</b>:  TLS Certificates relation. 
 - <b>`namespace`</b>:  Kubernetes namespace. 



**Returns:**
 
 - <b>`bool`</b>:  If the TLS certificate needs to be updated. 

---

<a href="../src/tls_relation.py#L96"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

### <kbd>function</kbd> `update_relation_data_fields`

```python
update_relation_data_fields(
    relation_fields: dict,
    tls_relation: Relation
) → None
```

Update a dict of items from the app relation databag. 



**Args:**
 
 - <b>`relation_fields`</b>:  items to update 
 - <b>`tls_relation`</b>:  TLS certificates relation 


