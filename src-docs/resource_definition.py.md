<!-- markdownlint-disable -->

<a href="../src/resource_definition.py#L0"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

# <kbd>module</kbd> `resource_definition.py`
gateway-api-integrator resource definition. 



---

## <kbd>class</kbd> `CharmConfig`
Charm configuration. 

Attrs:  gateway_class (_type_): _description_  external_hostname: The configured gateway hostname. 





---

## <kbd>class</kbd> `GatewayResourceInformation`
Base class containing kubernetes resource definition. 

Attrs:  config: The config data of the charm.  gateway_name: The gateway resource's name 




---

<a href="../src/resource_definition.py#L56"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

### <kbd>classmethod</kbd> `from_charm`

```python
from_charm(charm: CharmBase) → GatewayResourceInformation
```

Create a resource definition from charm instance. 



**Args:**
 
 - <b>`charm`</b> (ops.CharmBase):  _description_ 



**Raises:**
 
 - <b>`InvalidCharmConfigError`</b>:  _description_ 



**Returns:**
 
 - <b>`ResourceDefinition`</b>:  _description_ 


---

## <kbd>class</kbd> `InvalidCharmConfigError`
Exception raised when a charm configuration is found to be invalid. 

Attrs:  msg (str): Explanation of the error. 

<a href="../src/resource_definition.py#L21"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

### <kbd>function</kbd> `__init__`

```python
__init__(msg: str)
```

Initialize a new instance of the InvalidCharmConfigError exception. 



**Args:**
 
 - <b>`msg`</b> (str):  Explanation of the error. 





