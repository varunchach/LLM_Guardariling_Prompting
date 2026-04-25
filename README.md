# LLM Prompting & Deployment Demo

A complete student demo project built on **AWS Bedrock (Claude Sonnet 4.6)** covering:
1. **LLM Parameter Deep Dive** — every parameter with broken vs fixed examples
2. **Rapid Prototyping** — async, retry, cost tracking, prompt versioning
3. **Streamlit Chatbot** — streaming, logging, session stats
4. **Production Deployment** — Docker → AWS ECR → EC2 with CI/CD

---

## What's Inside

```
llm_streamlit_demo/
│
├── app/                            # Streamlit chatbot application
│   ├── app.py                      # Main UI — sidebar, chat, session logs
│   ├── llm_client.py               # Bedrock wrapper (invoke, stream, cost calc)
│   ├── logger.py                   # Per-call logger → pandas DataFrame
│   ├── requirements.txt            # boto3, streamlit, pandas
│   ├── Dockerfile                  # Container definition
│   ├── .streamlit/
│   │   └── config.toml             # Streamlit server config (CORS, WebSocket)
│   └── prompts/
│       ├── v1.txt                  # Vague prompt (intentionally bad)
│       └── v2.txt                  # Structured prompt (correct)
│
├── notebooks/
│   ├── 01_llm_apis_basics.ipynb    # 12-section parameter deep dive
│   └── 02_rapid_prototyping.ipynb  # Async, retry, cost, pipeline
│
├── .github/
│   └── workflows/
│       └── deploy.yml              # CI/CD: push to main → auto deploy to EC2
│
├── docker-compose.yml              # Local container run
├── userdata.sh                     # EC2 bootstrap script
├── .env.example                    # Credential template
└── README.md                       # This file
```

---

## Notebooks

### `01_llm_apis_basics.ipynb` — LLM Parameter Deep Dive

Every section shows ❌ broken first, then ✅ fixed.

| # | Parameter | What it shows |
|---|---|---|
| 1 | Credentials | Hardcoded keys crash → AWS CLI profile works |
| 2 | `system` | Generic response → 3 distinct personas (teacher / comedian / lawyer) |
| 3 | Streaming | All text dumps at once → word-by-word streaming |
| 4 | `temperature` | Convergent vs divergent tasks — 0.0 → 1.0 sweep + determinism proof |
| 5 | `max_tokens` | Response cut off mid-sentence at 30 / 100 / 300 tokens |
| 6 | `top_p` | Nucleus sampling at 0.1 / 0.5 / 0.9 |
| 7 | `top_k` | Uniqueness test — 3 runs each at k=1 / 10 / 250 |
| 8 | `stop_sequences` | All 10 list items generated → stops after item 3 |
| 9 | Multi-turn | Model forgets name → remembers with history → programmatic chat builder |
| 10 | Tool use | Hallucinated stock price → live yfinance lookup via 3-step tool flow |
| 11 | Penalty params | Repetition problem → system prompt workaround for Claude |
| 12 | Logging | Blind calls → DataFrame with per-call cost, latency, token breakdown |

### `02_rapid_prototyping.ipynb` — Rapid Prototyping

| # | Topic | What it shows |
|---|---|---|
| 1 | Async | Sequential (~12s for 5 calls) → concurrent ThreadPoolExecutor (~3s) |
| 2 | Retry | App crashes on API error → exponential backoff recovers silently |
| 3 | Cost tracking | No visibility → per-call cost table |
| 4 | Prompt versioning | Vague v1 output → structured parseable v2 output |
| 5 | Full pipeline | Input validation → versioned prompt → retry → output check → log |

---

## Streamlit App

Features:
- **Sidebar** — model selector, temperature, max tokens, system prompt, streaming toggle
- **Streaming mode** — tokens appear word-by-word as generated
- **Session stats** — total calls, total cost, average latency in sidebar
- **Session log** — expandable table with per-call breakdown at the bottom

---

## Prerequisites

- AWS account with **Bedrock access** (Claude Sonnet 4.6 enabled in `us-east-1`)
- AWS CLI installed and configured (`aws configure`)
- Python 3.10+
- Docker Desktop

---

## Setup — Step by Step

### Step 1 — Clone the repo

```bash
git clone https://github.com/varunchach/LLM_Guardariling_Prompting.git
cd LLM_Guardariling_Prompting/llm_streamlit_demo
```

### Step 2 — Configure AWS CLI

```bash
aws configure
```

Enter your:
- AWS Access Key ID
- AWS Secret Access Key
- Default region: `us-east-1`
- Output format: `json`

Verify it works:
```bash
aws sts get-caller-identity
```

### Step 3 — Run Notebooks

Open Jupyter and run the notebooks in order:

```bash
cd notebooks
jupyter notebook
```

Run `01_llm_apis_basics.ipynb` first, then `02_rapid_prototyping.ipynb`.

---

### Step 4 — Run Streamlit App Locally

```bash
cd app
pip install -r requirements.txt
streamlit run app.py
```

Open `http://localhost:8501`.

---

### Step 5 — Run with Docker Compose

**a) Create `.env` file:**
```bash
cp .env.example .env
```

Edit `.env`:
```
AWS_ACCESS_KEY_ID=your_access_key_id
AWS_SECRET_ACCESS_KEY=your_secret_access_key
AWS_DEFAULT_REGION=us-east-1
```

**b) Start Docker Desktop, then:**
```bash
docker compose up --build
```

Open `http://localhost:8501`. Verify container is running:
```bash
docker ps
```

---

### Step 6 — Deploy to AWS EC2

#### 6a — Create ECR repository

```bash
aws ecr create-repository --repository-name bedrock-chatbot --region us-east-1
```

#### 6b — Build and push Docker image

```bash
# Login to ECR (replace ACCOUNT_ID)
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin <ACCOUNT_ID>.dkr.ecr.us-east-1.amazonaws.com

# Build
docker build -t bedrock-chatbot ./app

# Tag
docker tag bedrock-chatbot:latest <ACCOUNT_ID>.dkr.ecr.us-east-1.amazonaws.com/bedrock-chatbot:latest

# Push
docker push <ACCOUNT_ID>.dkr.ecr.us-east-1.amazonaws.com/bedrock-chatbot:latest
```

#### 6c — Create IAM role for EC2

```bash
# Trust policy
python -c "
import json
policy = {
  'Version': '2012-10-17',
  'Statement': [{
    'Effect': 'Allow',
    'Principal': {'Service': 'ec2.amazonaws.com'},
    'Action': 'sts:AssumeRole'
  }]
}
open('ec2-trust.json', 'w').write(json.dumps(policy))
"

# Create role
aws iam create-role --role-name EC2BedrockRole --assume-role-policy-document file://ec2-trust.json

# Attach permissions
aws iam attach-role-policy --role-name EC2BedrockRole --policy-arn arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryReadOnly
aws iam attach-role-policy --role-name EC2BedrockRole --policy-arn arn:aws:iam::aws:policy/AmazonBedrockFullAccess

# Create instance profile
aws iam create-instance-profile --instance-profile-name EC2BedrockProfile
aws iam add-role-to-instance-profile --instance-profile-name EC2BedrockProfile --role-name EC2BedrockRole
```

#### 6d — Create key pair

```bash
aws ec2 create-key-pair --key-name bedrock-key --region us-east-1 --query "KeyMaterial" --output text > bedrock-key.pem
```

> Keep this file safe — never commit it to git.

#### 6e — Launch EC2 instance

```bash
aws ec2 run-instances --image-id ami-0c02fb55956c7d316 --instance-type t2.micro --region us-east-1 --iam-instance-profile Name=EC2BedrockProfile --key-name bedrock-key --user-data file://userdata.sh --tag-specifications "ResourceType=instance,Tags=[{Key=Name,Value=bedrock-chatbot}]" --query "Instances[0].InstanceId" --output text
```

#### 6f — Open port 8501

```bash
# Get security group ID
aws ec2 describe-instances --instance-ids <INSTANCE_ID> --region us-east-1 --query "Reservations[0].Instances[0].SecurityGroups[0].GroupId" --output text

# Open port
aws ec2 authorize-security-group-ingress --group-id <SG_ID> --protocol tcp --port 8501 --cidr 0.0.0.0/0 --region us-east-1
```

#### 6g — Get public IP and open app

```bash
aws ec2 describe-instances --instance-ids <INSTANCE_ID> --region us-east-1 --query "Reservations[0].Instances[0].PublicIpAddress" --output text
```

Wait 3-4 minutes for the bootstrap script to complete, then open:
```
http://<PUBLIC_IP>:8501
```

#### Instance management

```bash
# Stop when not using (saves cost)
aws ec2 stop-instances --instance-ids <INSTANCE_ID> --region us-east-1

# Start again
aws ec2 start-instances --instance-ids <INSTANCE_ID> --region us-east-1
```

---

### Step 7 — CI/CD (GitHub Actions)

Every push to `main` automatically rebuilds the Docker image and redeploys to EC2.

**Add these secrets to your GitHub repo** (`Settings → Secrets and variables → Actions`):

| Secret | Value |
|---|---|
| `AWS_ACCESS_KEY_ID` | Your AWS access key |
| `AWS_SECRET_ACCESS_KEY` | Your AWS secret key |
| `EC2_HOST` | EC2 public IP address |
| `EC2_SSH_KEY` | Contents of `bedrock-key.pem` |

Push any change to `main` — the Actions tab will show the pipeline running.

---

## Cost Reference

| Resource | Cost |
|---|---|
| Claude Sonnet 4.6 — input | $3.00 / 1M tokens |
| Claude Sonnet 4.6 — output | $15.00 / 1M tokens |
| EC2 t2.micro | Free tier (750 hrs/month) |
| ECR storage | $0.10 / GB / month |

> A typical chat message costs ~$0.000050. Stop the EC2 instance when not in use.

---

## Security Notes

- Never commit `.env` or `*.pem` files — both are in `.gitignore`
- EC2 uses an IAM role for Bedrock and ECR access — no credentials stored on the instance
- For production, restrict port 8501 to specific IPs instead of `0.0.0.0/0`
