# TrustEdge Device Certificate Lifecycle and Attributes Setup

Prerequisite: To manage certificate lifecycle with TrustEdge on any OS, the device must first be registered in Device Trust Manager and download the device Birth certificate or Bootstrap certificate.

Use one of the options below. Both are simple copy-paste setups.

## Option 1: Use an environment file (recommended)

1. Copy the CA and ICA certificates into the trust store. Replace `root.pem` and `ica.pem` with your actual certificate file names:

```bash
cp root.pem ica.pem /etc/digicert/keystore/ca/
```

Example: use your real CA and ICA certificate files instead of the placeholders `root.pem` and `ica.pem`.

2. Make sure the sample file [attributes.json](attributes.json) is present at `/etc/digicert/conf/attributes.json` before starting the agent. This file contains your custom inventory attributes. Example below just sets variable "SERIAL_NUMBER" as environment variable and same TrustEdge can read and map to the certifcate issued from Device Trust Manager.

```bash 
{
    "attributes": [
        {
            "attribute_name": "serial_number",
            "attribute_value": {
                "type": "ENV",
                "variable_name": "SERIAL_NUMBER"
            }
        },
        {
            "attribute_name": "...",
            "attribute_value": {
                "type": "program",
                "path": "${program_path}",
                "argument": "...."
            }
        },
        {
            "attribute_names": [
                "...",
                "..."
            ],
            "attribute_value": {
                "type": "program",
                "path": "${program_path}",
                "output_format": "TOML|JSON",
                "argument": "...."
            }
        }
    ]
}
```


3. Edit the systemd TrustEdge service file:

```bash
sudo vi /etc/systemd/system/trustedge.service
```

Include:

```ini
[Service]
EnvironmentFile=/etc/digicert/device.env
```

4. Create the environment file:

```bash
sudo vi /etc/digicert/device.env
```

Add:

```bash
SERIAL_NUMBER=123ABC
```

5. Configure the TrustEdge agent using the bootstrap ZIP downloaded from Device Trust Manager:

```bash
sudo trustedge agent --configure --bootstrap-zip /path/to/downloaded/bootstrap.zip
```

Replace `/path/to/downloaded/bootstrap.zip` with the actual file you downloaded from Device Trust Manager.

6. Reload systemd and restart the service:

```bash
sudo systemctl daemon-reload
sudo systemctl restart trustedge.service
```

## Option 2: Set the variable directly in the service

If you do not want to use a separate environment file, add the variable directly:

```bash
sudo systemctl edit trustedge.service
```

Then add:

```ini
[Service]
Environment="SERIAL_NUMBER=123ABC"
```

Then apply:

```bash
sudo systemctl daemon-reload
sudo systemctl restart trustedge.service
```

## Refresh custom attributes

If the agent keeps using old values, remove the existing metrics file so it rereads [attributes.json](attributes.json):

```bash
sudo systemctl stop trustedge.service
sudo mv /etc/digicert/conf/metrics.pb /etc/digicert/conf/metrics.pb.bak
sudo systemctl daemon-reload
sudo systemctl restart trustedge.service
```

Note: when `metrics.pb` already exists, the agent loads stored metrics and skips reading [attributes.json](attributes.json). If the file is missing, the agent reads [attributes.json](attributes.json) and creates a new `metrics.pb`.

## Quick summary

- Preferred: `EnvironmentFile=/etc/digicert/myenv.env`
- Alternative: `Environment="SERIAL_NUMBER=123ABC"`
- To force a refresh: rename or remove `metrics.pb` and restart the service
