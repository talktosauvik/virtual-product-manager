# Synchrony Golden Microservice Code Templates

## 1. Safe JSON Regex Sanitizer (`proxy_gateway.py` Core Pattern)

```python
import json
import re
from typing import Any

PAN_REGEX = re.compile(r"\b(?:\d[ -]*?){13,16}\b")
SSN_REGEX = re.compile(r"\b\d{3}-\d{2}-\d{4}\b")
MRN_REGEX = re.compile(r"\bMRN-\d{6,10}\b")

def sanitize_telemetry_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """Safely scrub PCI-DSS (PAN/SSN) and CareCredit HIPAA (MRN) tokens without eval()."""
    raw_json = json.dumps(payload)
    scrubbed = SSN_REGEX.sub("[REDACTED_SSN]", raw_json)
    scrubbed = MRN_REGEX.sub("[REDACTED_MRN]", scrubbed)
    scrubbed = PAN_REGEX.sub("[REDACTED_PAN]", scrubbed)
    return json.loads(scrubbed)
```

## 2. Hardened Red Hat UBI9 `Dockerfile`

```dockerfile
FROM registry.access.redhat.com/ubi9/python-312:latest
LABEL maintainer="SYF-Platform-Mesh-Squad <ai-platform@syf.bank>"
LABEL com.synchrony.compliance="pci-dss-v4.0-hipaa-tier1"

WORKDIR /opt/app-root/src
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY proxy_gateway.py .
USER 1001
EXPOSE 8080
CMD ["uvicorn", "proxy_gateway:app", "--host", "0.0.0.0", "--port", "8080", "--workers", "4"]
```
