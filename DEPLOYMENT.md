# Deploying Resume Analyzer to AWS EC2

This guide walks through deploying the app on an **AWS EC2** instance, with
**S3** for resume storage and **DynamoDB** for results. It reflects the exact
setup used for this project (region **`ap-south-1`** / Mumbai).

> **Cost warning:** these steps create billable AWS resources. Everything
> here fits the AWS Free Tier if you use a `t2.micro` instance, but you must
> **tear it all down** when finished (see the last section) to avoid charges.

---

## 0. Prerequisites

- An AWS account.
- A **Groq API key** — <https://console.groq.com/keys>.
- An SSH client (built into Windows 10/11, macOS, and Linux).
- The app pushed to a Git repo you control (this repo).

Everything below can be done in the **AWS Console** (web UI). Keep the region
selector (top-right) on **Asia Pacific (Mumbai) `ap-south-1`** for every step so
all resources live in the same region.

---

## 1. Create an IAM user (do not use root keys)

Never use AWS **root** access keys for an app. Create a dedicated IAM user:

1. Console → **IAM** → **Users** → **Create user**.
2. Name it `resume-analyzer-app`.
3. Attach permissions. For least privilege, create an inline policy allowing:
   - `s3:PutObject`, `s3:GetObject`, `s3:ListBucket` on your bucket, and
   - `dynamodb:PutItem`, `dynamodb:GetItem`, `dynamodb:Query`, `dynamodb:Scan`
     on your table.
   (For a quick class demo you may instead attach the managed policies
   `AmazonS3FullAccess` and `AmazonDynamoDBFullAccess` — but remove them after.)
4. Open the user → **Security credentials** → **Create access key** → choose
   "Application running outside AWS". Save the **Access key ID** and **Secret**.

> These two values become `AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY` in the
> app's `.env`.

---

## 2. Create the S3 bucket (resume storage)

1. Console → **S3** → **Create bucket**.
2. **Bucket name:** must be globally unique. If `resume-analyzer-app-bucket` is
   taken, append something unique, e.g. `resume-analyzer-app-bucket-<account-id>`.
3. **Region:** `ap-south-1`.
4. Leave **Block all public access** ON (the app accesses it with credentials,
   not publicly).
5. Create.

> Put the final bucket name in `.env` as `S3_BUCKET=...`.

---

## 3. Create the DynamoDB table (results)

1. Console → **DynamoDB** → **Tables** → **Create table**.
2. **Table name:** `resume-analyzer`.
3. **Partition key:** `id` (type **String**).
4. **Capacity:** choose **On-demand** (no fixed hourly cost).
5. Create and wait until status is **Active**.

> If you use a different table name, set `DYNAMODB_TABLE=...` in `.env`.

---

## 4. Launch the EC2 instance (the server)

1. Console → **EC2** → **Instances** → **Launch instances**.
2. **Name:** `resume-analyzer-ec2`.
3. **AMI:** Amazon Linux 2023 (x86_64).
4. **Instance type:** `t2.micro` (Free Tier eligible).
5. **Key pair:** create a new one named `resume-analyzer-key`, download the
   `.pem` file, and keep it safe — you need it to SSH in.
6. **Network / Security group:** create a security group with inbound rules:
   - **SSH** — TCP **22** — source: *My IP* (more secure) or Anywhere.
   - **Custom TCP** — TCP **8501** — source: Anywhere `0.0.0.0/0` (so you can
     open the app in a browser).
7. **Storage:** default 8 GB is fine.
8. Launch.

Once the instance is **Running**, note its **Public IPv4 address**.

### (Optional) User-data to auto-install on boot
When launching, you can paste this into **Advanced details → User data** so the
box configures itself on first boot:

```bash
#!/bin/bash
dnf update -y
dnf install -y python3 python3-pip git
cd /home/ec2-user
git clone https://github.com/VinayakMokashi/resume-analyzer-app.git
cd resume-analyzer-app
python3 -m venv venv
./venv/bin/pip install --upgrade pip
./venv/bin/pip install -r requirements.txt
chown -R ec2-user:ec2-user /home/ec2-user/resume-analyzer-app
```

---

## 5. Connect and configure

### Fix the key permissions (once, on your machine)
SSH refuses keys that others can read.

- **macOS/Linux:** `chmod 400 resume-analyzer-key.pem`
- **Windows (PowerShell):**
  ```powershell
  icacls "resume-analyzer-key.pem" /inheritance:r
  icacls "resume-analyzer-key.pem" /grant:r "$($env:USERNAME):(R)"
  ```

### SSH into the instance
```bash
ssh -i resume-analyzer-key.pem ec2-user@<PUBLIC_IP>
```

### If you did NOT use user-data, install now
```bash
sudo dnf update -y
sudo dnf install -y python3 python3-pip git
git clone https://github.com/VinayakMokashi/resume-analyzer-app.git
cd resume-analyzer-app
python3 -m venv venv
./venv/bin/pip install --upgrade pip
./venv/bin/pip install -r requirements.txt
```

### Create the `.env` on the server
`.env` is intentionally not in the repo, so create it on the instance:
```bash
cd /home/ec2-user/resume-analyzer-app
cat > .env <<'EOF'
GROQ_API_KEY=your_groq_key_here
AWS_ACCESS_KEY_ID=your_iam_key
AWS_SECRET_ACCESS_KEY=your_iam_secret
AWS_REGION=ap-south-1
S3_BUCKET=your_bucket_name
DYNAMODB_TABLE=resume-analyzer
EOF
```

---

## 6. Run the app as a service

Running it as a `systemd` service keeps it alive after you log out and restarts
it on crash/reboot.

```bash
sudo tee /etc/systemd/system/resume-analyzer.service > /dev/null <<'EOF'
[Unit]
Description=Resume Analyzer Streamlit App
After=network.target

[Service]
User=ec2-user
WorkingDirectory=/home/ec2-user/resume-analyzer-app
ExecStart=/home/ec2-user/resume-analyzer-app/venv/bin/streamlit run main.py --server.port 8501 --server.address 0.0.0.0 --server.headless true
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable resume-analyzer
sudo systemctl start resume-analyzer
```

**Open the app:** `http://<PUBLIC_IP>:8501`

### Useful management commands
```bash
sudo systemctl status resume-analyzer     # is it running?
sudo systemctl restart resume-analyzer    # restart after a code change
sudo journalctl -u resume-analyzer -f     # live logs
```

### Deploying code changes later
```bash
cd /home/ec2-user/resume-analyzer-app
git pull
sudo systemctl restart resume-analyzer
```

---

## 7. Verify

```bash
curl http://<PUBLIC_IP>:8501/_stcore/health   # should print: ok
```
Then open `http://<PUBLIC_IP>:8501` in a browser, upload a resume + paste a job
description, and click **Analyze Resume**.

---

## 8. Teardown (delete everything to stop charges)

Do these in the Console when you are finished:

1. **EC2** → select the instance → **Instance state → Terminate**.
2. **EC2 → Key Pairs** → delete `resume-analyzer-key`.
3. **EC2 → Security Groups** → delete `resume-analyzer-sg`.
4. **S3** → empty the bucket, then delete it.
5. **DynamoDB** → delete the `resume-analyzer` table.
6. **IAM** → if you attached temporary full-access policies, detach them (or
   delete the user if you no longer need it).

After teardown, confirm in **Billing → Cost Explorer** that usage has stopped.
