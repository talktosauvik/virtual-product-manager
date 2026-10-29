# Synchrony Financial Security, Compliance & Network Control Matrix

| Control Domain | Standard / Regulation | Mandatory Synchrony Implementation | Non-Compliance Action |
| :--- | :--- | :--- | :--- |
| **Cardholder Data (CHD)** | PCI-DSS v4.0 Req 3 & 4 | Inline regex + DLP scrubbing of 15/16-digit PAN (`[REDACTED_PAN]`) and 9-digit SSN (`[REDACTED_SSN]`) before ClickHouse storage. | Block deployment; reject SaaS egress. |
| **Healthcare Financing (CareCredit)** | HIPAA Security & Privacy Rule | Inline scrubbing of Medical Record Numbers (`MRN-\d+` -> `[REDACTED_MRN]`) and ICD-10 diagnosis codes (`[REDACTED_PHI]`). BAA + zero external egress. | Require `SYF-SecOps-DLP-Squad` sign-off (`+1 sprint` if DLP sidecar added). |
| **Workload Identity & AuthN** | SYF IAM-STD-04 (Entra ID) | OAuth 2.0 / OIDC JWT bearer token verification via Microsoft Entra ID (`mTLS 1.3`) under `<25ms` P95 proxy latency SLA. | Block unauthenticated or non-mTLS telemetry ingestion. |
| **Service Ingress & Gateway** | SYF NET-STD-09 (Baseline v1.0) | Baseline v1.0 ingress routes via Kong Enterprise API Gateway v3.4 (`kong-ingress.syf.bank`) with OAuth 2.0 JWT validation and `<25ms` P95 proxy SLA. | Enforce `<25ms` P95 latency and mTLS 1.3 termination. |
| **Container Runtime** | SYFPLAT-ROSA-01 / GCP-CR-02 | Red Hat UBI9 (`ubi9/python-312`) running as non-root UID `1001` on AWS ROSA or Google Cloud Run Private Subnets. | Block container image promotion in Bitbucket pipeline. |
