# Resume Analyzer

An AI-powered web app that compares a candidate's **resume** against a **job
description** and returns a structured fit analysis — a match score, matching
qualifications, missing skills, strengths, and concrete suggestions for
improvement.

It is built with **Streamlit** for the UI, uses the **Groq LLM API** for the
analysis, and integrates with **AWS** (S3 + DynamoDB) for cloud storage. It is
designed to be deployed on an **AWS EC2** instance.

---

## Features

- 📄 Upload a resume as a PDF and paste a target job description
- 🤖 AI analysis via Groq (default model: `qwen/qwen3-32b`, a reasoning model)
- 🧠 Separates the model's reasoning ("Thinking") from its final answer
- ☁️ Stores uploaded resumes in **Amazon S3**
- 🗃️ Stores each analysis + metadata in **Amazon DynamoDB**
- ⬇️ Download the analysis as a text file
- 🛟 Runs fine locally with **no AWS at all** (cloud writes are best-effort)

---

## Architecture

```
                +-------------------------+
   Browser  --> |   Streamlit UI (EC2)    |
                |        main.py          |
                +-----------+-------------+
                            |
        +-------------------+--------------------+
        |                   |                    |
        v                   v                    v
  +-----------+      +-------------+      +---------------+
  | Groq API  |      |  Amazon S3  |      | Amazon DynamoDB|
  | (LLM)     |      | (resumes)   |      | (results)      |
  +-----------+      +-------------+      +---------------+
```

- **EC2** hosts the Streamlit app (run as a `systemd` service).
- **Groq** produces the analysis text.
- **S3** stores the uploaded PDF.
- **DynamoDB** stores the parsed resume + the analysis result + form metadata.

---

## Tech stack

| Area      | Technology                        |
|-----------|-----------------------------------|
| UI        | Streamlit                         |
| LLM       | Groq API (`qwen/qwen3-32b`)       |
| PDF parse | PyPDF2                            |
| Cloud     | AWS S3, AWS DynamoDB, AWS EC2     |
| SDK       | boto3                             |
| Config    | python-dotenv (`.env`)            |
| Runtime   | Python 3.9+ (3.10+ recommended)   |

---

## Repository structure

```
resume-analyzer-app/
├── main.py                 # The entire Streamlit app
├── requirements.txt        # Python dependencies
├── .env.example            # Template for environment variables (copy to .env)
├── .streamlit/config.toml  # Streamlit config (logging level)
├── DEPLOYMENT.md           # Full step-by-step AWS EC2 deployment guide
├── screenshots/            # Screenshots of the running app + AWS resources
└── README.md               # This file
```

---

## Quickstart (run locally)

### 1. Prerequisites
- Python 3.9+ installed
- A free **Groq API key** — get one at <https://console.groq.com/keys>
- (Optional) AWS credentials if you want S3 + DynamoDB storage

### 2. Clone and enter the project
```bash
git clone https://github.com/VinayakMokashi/resume-analyzer-app.git
cd resume-analyzer-app
```

### 3. Create a virtual environment and install dependencies
```bash
python -m venv venv
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

pip install -r requirements.txt
```

### 4. Configure environment variables
```bash
cp .env.example .env      # (Windows: copy .env.example .env)
```
Open `.env` and set at least your `GROQ_API_KEY` (see the table below).

### 5. Run the app
```bash
streamlit run main.py
```
Open the URL Streamlit prints (usually <http://localhost:8501>).

---

## Configuration (`.env`)

| Variable                | Required | Default                      | Description |
|-------------------------|----------|------------------------------|-------------|
| `GROQ_API_KEY`          | **Yes**  | —                            | Your Groq API key. Without it the analysis call fails. |
| `GROQ_MODEL`            | No       | `qwen/qwen3-32b`             | Override the Groq model. See <https://console.groq.com/docs/models>. |
| `AWS_ACCESS_KEY_ID`     | No       | —                            | AWS key. Leave blank to skip cloud storage. |
| `AWS_SECRET_ACCESS_KEY` | No       | —                            | AWS secret. |
| `AWS_REGION`            | No       | `ap-south-1`                 | AWS region for S3 + DynamoDB. |
| `S3_BUCKET`             | No       | `resume-analyzer-app-bucket` | S3 bucket name for uploaded resumes. |
| `DYNAMODB_TABLE`        | No       | `resume-analyzer`            | DynamoDB table name for results. |

> **Never commit `.env`.** It is git-ignored on purpose. Only `.env.example`
> (with empty values) is tracked.

> **AWS is optional.** All AWS calls are wrapped in `try/except`, so if
> credentials or resources are missing the app still runs and analyzes resumes —
> it just skips the S3/DynamoDB writes.

---

## Deploy to AWS EC2

The full, reproducible, click-by-click guide (IAM user, S3 bucket, DynamoDB
table, EC2 launch, security group, and running the app as a service) lives in
**[DEPLOYMENT.md](DEPLOYMENT.md)**.

---

## How the code works (`main.py`)

The app is a single file organized into three layers:

**1. Setup & AWS helpers**
- Loads environment variables with `load_dotenv()`.
- Builds a DynamoDB resource from the AWS credentials.
- `upload_item_to_dynamodb(table_name, item)` — writes one record to DynamoDB.
- `upload_file(file_path, bucket, object_name)` — uploads a file to S3.
- All of this is wrapped in `try/except` so a missing/misconfigured AWS setup
  never crashes the app.

**2. Core logic**
- `initialize_groq_client()` — creates the Groq client from `GROQ_API_KEY`.
- `extract_text_from_pdf(pdf_file)` — extracts text from the uploaded PDF.
- `analyze_resume(client, resume_text, job_description)` — builds the prompt,
  calls the Groq model, returns the analysis text.
- `split_thinking(analysis)` — splits a reasoning model's `<think>…</think>`
  block from its final answer, safely handling responses without one.

**3. UI & orchestration (`main`)**
- Renders the form (candidate details, PDF uploader, job description).
- When both a resume and a job description are present: saves + uploads the PDF
  to S3, extracts the text, and on **Analyze**: calls Groq, saves the result to
  DynamoDB, renders the "Thinking" and "Response" boxes, and offers a download.

---

## Cost & teardown ⚠️

Running this on AWS creates billable resources. When you are done, **delete
them** to avoid charges:

- **EC2 instance** — the main cost. Stop it to pause charges, terminate it to
  delete. Also delete its **key pair** and **security group**.
- **S3 bucket** — empty it, then delete it.
- **DynamoDB table** — delete it.

See the teardown checklist at the end of **[DEPLOYMENT.md](DEPLOYMENT.md)**.

---

## License

This project is for educational purposes.
