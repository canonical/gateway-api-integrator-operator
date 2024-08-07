<!-- markdownlint-disable -->

<a href="../src/charm.py#L0"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

# <kbd>module</kbd> `charm.py`
gateway-api-integrator charm file. 

**Global Variables**
---------------
- **CREATED_BY_LABEL**
- **INGRESS_RELATION**
- **TLS_CERT_RELATION**


---

## <kbd>class</kbd> `GatewayAPICharm`
The main charm class for the gateway-api-integrator charm. 

<a href="../src/charm.py#L88"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

### <kbd>function</kbd> `__init__`

```python
__init__(*args) → None
```

Init method for the class. 



**Args:**
 
 - <b>`args`</b>:  Variable list of positional arguments passed to the parent constructor. 


---

#### <kbd>property</kbd> app

Application that this unit is part of. 

---

#### <kbd>property</kbd> charm_dir

Root directory of the charm as it is running. 

---

#### <kbd>property</kbd> config

A mapping containing the charm's config and current values. 

---

#### <kbd>property</kbd> meta

Metadata of this charm. 

---

#### <kbd>property</kbd> model

Shortcut for more simple access the model. 

---

#### <kbd>property</kbd> unit

Unit that this execution is responsible for. 




---

## <kbd>class</kbd> `LightKubeInitializationError`
Exception raised when initialization of the lightkube client failed. 





