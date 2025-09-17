# DigiCert<sup>®</sup> TrustEdge

TrustEdge is a standalone executable that can run as both an **agent** for devices managed through [DigiCert<sup>®</sup> Device Trust Manager](https://www.digicert.com/device-trust-manager) or as a standalone **command line** tool for performing common security tasks on a device, such as generating keys and submitting a certificate signing request (CSR) to a certificate authority (CA). TrustEdge is built using the open source [DigiCert<sup>®</sup> TrustCore SDK](https://www.digicert.com/iot/trustcore-sdk). TrustEdge includes the latest post quantum cryptographic (PQC) algorithms such as ML-DSA, SLH-DSA and ML-KEM, plus TLS 1.3 support.

> [!NOTE]
> DigiCert is in the process of completely open-sourcing the code under the AGPL v3 license to support transparency, collaboration, and developer accessibility, while maintaining commercial licensing for commercial and proprietary use.

## Agent mode

When run in agent mode, TrustEdge acts as a client to DigiCert<sup>®</sup> Device Trust Manager. It runs as daemon (Linux) on an IoT device and uses MQTT for all communications between the device and Device Trust Manager.

TrustEdge agent can:

- Authenticate a device with Device Trust Manager using bootstrap credentials such as an x.509 "birth" certificate.
- Interface with secure hardware elements on a device, such as a TPM.
- Exchange bootstrap credentials for an "operational" x.509 certificate for accessing cloud services such as an MQTT broker running in the cloud.
- Renew an operational certificate.
- Download and install over-the-air updates.
- Report device properties directly to Device Trust Manager. For example, IP address, MAC address, or location.

## Command line mode

TrustEdge can also run as a standalone command line interface (CLI) tool without the need for Device Trust Manager. TrustEdge command line is useful for prototyping and accelerating an IoT pilot or proof of concept. You can use it to perform common security tasks on an IoT device.

TrustEdge command line can:

- Generate keys (For example, RSA, ECDSA, ML-DSA, SLH-DSA)
- Create a CSR.
- Submit a CSR to a CA and obtain a certificate.
- Renew a certificate.
- Communicate with an MQTT broker over TLS using x.509 authentication.

Rather than learning and using multiple OSS tools to accomplish the above tasks, TrustEdge command line brings all these capabilties into one easy-to-use tool.

## Documentation

TrustEdge documentation is available at https://dev.digicert.com/en/trustedge.html.

## License

This project is available under a **dual-license model**:

- **Open Source License:**  
  [GNU Affero General Public License v3 (AGPL v3)](./LICENSE.md)
  This license allows you to use, modify, and distribute the code for free in accordance with AGPL terms.

- **Commercial License:**  
If you wish to use TrustCore SDK in a **proprietary** or **commercial** product (e.g., embedded in closed-source firmware or commercial SaaS applications), a commercial license is available under DigiCert’s [Master Services Agreement](https://www.digicert.com/master-services-agreement/) (MSA).  Contact us at [sales@digicert.com](mailto:sales@digicert.com) for commercial licensing details.

## Contributing

We welcome contributions that improve TrustCore SDK! Please follow these steps:

1. Fork the repository
2. Create a feature branch
3. Make your changes with clear commits
4. Submit a pull request
5. Review and accept the [Contributor License Agreement (CLA)](CONTRIBUTING.md)

## Contributor License Agreement (CLA)

All contributors must agree to a **Contributor License Agreement (CLA)** before we can accept your pull request. By submitting a pull request, you agree to the terms of the CLA.

By contributing, you agree that DigiCert may license your contributions under both:

- AGPL v3 (open source), and
- DigiCert’s commercial licensing terms

To learn more, see [CONTRIBUTING.md](CONTRIBUTING.md). We may use an integrated tool to enforce CLA acceptance during the pull request process.

## Legal and Compliance Notes

- This project uses a **copyleft license (AGPL v3)**. If you include this code in a larger application, you may be required to release the source of that application under AGPL.
- If you are unsure whether your intended use triggers AGPL obligations, please reach out to [legal@digicert.com](mailto:opensourcelegal@digicert.com) for clarification or [sales@digicert.com](mailto:sales@digicert.com) for commercial options.

## Reporting a Vulnerability

We encourage responsible disclosure of security vulnerabilities.
If you find something suspicious, we encourage and appreciate your report! To learn more, see [SECURITY.md](SECURITY.md).

## Contact

- Commercial licensing: [sales@digicert.com](mailto:sales@digicert.com)
- General inquiries: [support@digicert.com](mailto:support@digicert.com)

---

(c) 2025 DigiCert, Inc. All rights reserved.