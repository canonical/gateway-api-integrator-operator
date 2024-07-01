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

<a href="../src/tls_relation.py#L30"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

### <kbd>function</kbd> `__init__`

```python
__init__(model: Model) → None
```

Init method for the class. 



**Args:**
 
 - <b>`model`</b>:  The charm model used to get the relations and secrets. 




---

<a href="../src/tls_relation.py#L174"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

### <kbd>function</kbd> `certificate_expiring`

```python
certificate_expiring(
    event: Union[CertificateExpiringEvent, CertificateInvalidatedEvent],
    certificates: TLSCertificatesRequiresV3,
    tls_integration: Relation
) → None
```

Handle the TLS Certificate expiring event. 



**Args:**
 
 - <b>`event`</b>:  The event that fires this method. 
 - <b>`certificates`</b>:  The certificate requirer library instance. 
 - <b>`tls_integration`</b>:  The tls certificates integration. 

---

<a href="../src/tls_relation.py#L155"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

### <kbd>function</kbd> `certificate_relation_available`

```python
certificate_relation_available(
    event: CertificateAvailableEvent,
    tls_integration: Relation
) → None
```

Handle the TLS Certificate available event. 



**Args:**
 
 - <b>`event`</b>:  The event that fires this method. 
 - <b>`tls_integration`</b>:  The tls certificates integration. 

---

<a href="../src/tls_relation.py#L132"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

### <kbd>function</kbd> `certificate_relation_created`

```python
certificate_relation_created(hostname: str, tls_integration: Relation) → None
```

Handle the TLS Certificate created event. 



**Args:**
 
 - <b>`hostname`</b>:  Certificate's hostname. 
 - <b>`tls_integration`</b>:  The tls certificates integration. 

---

<a href="../src/tls_relation.py#L109"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

### <kbd>function</kbd> `certificate_relation_joined`

```python
certificate_relation_joined(
    hostname: str,
    certificates: TLSCertificatesRequiresV3,
    tls_integration: Relation
) → None
```

Handle the TLS Certificate joined event. 



**Args:**
 
 - <b>`hostname`</b>:  Certificate's hostname. 
 - <b>`certificates`</b>:  The certificate requirer library instance. 
 - <b>`tls_integration`</b>:  The tls certificates integration. 

---

<a href="../src/tls_relation.py#L39"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

### <kbd>function</kbd> `generate_password`

```python
generate_password() → str
```

Generate a random 12 character password. 



**Returns:**
 
 - <b>`str`</b>:  Private key string. 

---

<a href="../src/tls_relation.py#L91"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

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

<a href="../src/tls_relation.py#L72"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

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

<a href="../src/tls_relation.py#L58"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

### <kbd>function</kbd> `pop_relation_data_fields`

```python
pop_relation_data_fields(relation_fields: list, tls_relation: Relation) → None
```

Pop a list of items from the app relation databag. 



**Args:**
 
 - <b>`relation_fields`</b>:  items to pop 
 - <b>`tls_relation`</b>:  TLS certificates relation 

---

<a href="../src/tls_relation.py#L48"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

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


