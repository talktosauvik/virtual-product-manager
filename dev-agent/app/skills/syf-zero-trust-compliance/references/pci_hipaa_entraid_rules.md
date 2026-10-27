# Synchrony Financial Security, Compliance & Network Control Matrix

| Control Domain | Standard / Regulation | Mandatory Synchrony Implementation | Non-Compliance Action |
| :--- | :--- | :--- | :--- |
| **Cardholder Data (CHD)** | PCI-DSS v4.0 Req 3 & 4 | Inline regex + DLP scrubbing of 15/16-digit PAN (`[REDACTED_PAN]`) and 9-digit SSN (`[REDACTED_SSN]`) before ClickHouse storage. | Block deployment; reject SaaS egress. |
| **Healthcare Financing (CareCredit)** | HIPAA Security & Privacy Rule | Inline scrubbing of Medical Record Numbers (`MRN-\d+` -> `[REDACTED_MRN]`) and ICD-10 diagnosis codes (`[REDACTED_PHI]`). BAA + zero external egress. | Require `SYF-SecOps-DLP-Squad` sign-off (`+1 sprint` if DLP sidecar added). |
| **Workload Identity & AuthN** | SYF IAM-STD-04 (Entra ID) | OAuth 2.0 JWT validation via Microsoft Entra ID JWKS endpoint cached locally (`TTL=300s`). | Reject synchronous introspection if P95 > 25ms. |
| **Service Ingress & Mesh** | SYF NET-STD-09 (Q1 Update) | Envoy Service Mesh sidecar (`mesh.syf.bank/injected: "true"`) with mTLS 1.3. **Kong Gateway v3.4 is DEPRECATED.** | Trigger `CB-1` migration (`+2 sprints`, `+$32,000` mesh integration). |
| **Container Runtime** | SYFPLAT-ROSA-01 / GCP-CR-02 | Red Hat UBI9 (`ubi9/python-312`) running as non-root UID `1001` on AWS ROSA or Google Cloud Run Private Subnets. | Block container image promotion in Bitbucket pipeline. |
