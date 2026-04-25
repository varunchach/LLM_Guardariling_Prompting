# Bedrock Chatbot — LLM Demo Project

A student demo covering three topics end-to-end:
1. **LLM APIs & Streamlit Bot** — parameters, streaming, logging
2. **Rapid Prototyping** — async, retry, cost tracking, prompt versioning
3. **Deployment** — Docker Compose → AWS EC2 + CI/CD

**Model:** Claude Sonnet 4.6 via AWS Bedrock (`us.anthropic.claude-sonnet-4-6`)

---

## Project Structure

```
llm_streamlit_demo/
│
├── app/                           # Streamlit application
│   ├── app.py                     # Main Streamlit UI
│   ├── llm_client.py              # Bedrock API wrapper (invoke, stream, cost)
│   ├── logger.py                  # Session call logger → pandas DataFrame
│   ├── requirements.txt           # Python dependencies
│   ├── Dockerfile                 # Container definition
│   ├── .streamlit/
│   │   └── config.toml            # Streamlit server config (CORS, WebSocket)
│   └── prompts/
│       ├── v1.txt                 # Vague prompt template (intentionally bad)
│       └── v2.txt                 # Structured prompt template (correct)
│
├── notebooks/
│   ├── 01_llm_apis_basics.ipynb   # 12-section parameter deep dive
│   └── 02_rapid_prototyping.ipynb # Async, retry, cost, versioning, pipeline
│
├── .github/
│   └── workflows/
│       └── deploy.yml             # CI/CD: GitHub Actions → ECR → EC2
│
├── docker-compose.yml             # Local container run
├── userdata.sh                    # EC2 bootstrap script (auto-installs Docker + runs container)
├── .env.example                   # Environment variable template
├── .env                           # Your actual credentials (never commit)
└── README.md                      # This file
```

---

## File Descriptions

### `app/app.py`
Streamlit chatbot UI. Features:
- Sidebar: model selector, temperature slider, max tokens slider, system prompt input, streaming toggle
- Live session stats: total calls, total cost, average latency
- Streaming and non-streaming response modes
- Expandable session log table at the bottom

### `app/llm_client.py`
Core Bedrock wrapper used by both the app and notebooks:
- `invoke_model()` — blocking call, returns text + token usage + cost
- `stream_response()` — generator for `st.write_stream`, yields text chunks
- `calculate_cost()` — per-call USD cost from token counts
- Credentials: reads from `~/.aws/credentials` locally, IAM role on EC2

### `app/logger.py`
Appends each call's metadata (prompt, response preview, tokens, latency, cost) to `st.session_state` and returns it as a pandas DataFrame.

### `app/.streamlit/config.toml`
Streamlit server configuration — disables CORS and XSRF protection so the app works correctly behind Docker and EC2 networking.

### `app/prompts/v1.txt`
```
Summarize this text: {text}
```
Intentionally vague — used in Notebook 2 to show why prompt versioning matters.

### `app/prompts/v2.txt`
Structured 3-bullet prompt with action verbs — produces consistent, parseable output.

### `notebooks/01_llm_apis_basics.ipynb`
12 sections, each showing a broken approach then the fix:

| Section | Parameter | Demo |
|---|---|---|
| 1 | Credentials | Hardcoded keys crash → AWS CLI profile |
| 2 | `system` | No persona → teacher / comedian / lawyer |
| 3 | Streaming | Blocking dump → word-by-word tokens |
| 4 | `temperature` | Convergent vs divergent tasks, 0.0–1.0 sweep |
| 5 | `max_tokens` | Cut-off detection at 30 / 100 / 300 tokens |
| 6 | `top_p` | Nucleus sampling at 0.1 / 0.5 / 0.9 |
| 7 | `top_k` | Uniqueness test across 3 runs per k value |
| 8 | `stop_sequences` | Full list vs stopped at item 3 |
| 9 | Multi-turn messages | No history → forgot name / with history → remembered |
| 10 | Tool use | Hallucinated price → live yfinance stock lookup |
| 11 | Penalty params | System prompt workaround for Claude |
| 12 | Logging | Blind calls → DataFrame with cost + latency analysis |

### `notebooks/02_rapid_prototyping.ipynb`
5 sections:

| Section | Demo |
|---|---|
| 1 | Sequential calls (~12s) vs async ThreadPoolExecutor (~3s) |
| 2 | No retry crashes → exponential backoff recovers silently |
| 3 | No cost tracking → per-call cost DataFrame |
| 4 | Prompt v1 (vague) vs v2 (structured, parseable) |
| 5 | Full production pipeline: validate → prompt → retry → log → return |

### `deploy.yml`
GitHub Actions workflow triggered on push to `main`:
1. Authenticates to AWS using repository secrets
2. Logs in to ECR, builds and pushes Docker image
3. SSHs into EC2, pulls latest image and restarts the container

### `userdata.sh`
EC2 bootstrap script passed as UserData on instance launch. Automatically installs Docker, authenticates to ECR, and starts the container — no manual SSH required.

---

## Prerequisites

- AWS account with Bedrock access (Claude Sonnet 4.6 enabled in `us-east-1`)
- AWS CLI configured (`aws configure`)
- Python 3.10+
- Docker Desktop

---

## Step 1 — Run Locally with Python

```bash
cd llm_streamlit_demo/app
pip install -r requirements.txt
streamlit run app.py
```

Open `http://localhost:8501`. Uses `~/.aws/credentials` default profile automatically.

---

## Step 2 — Run with Docker Compose

**a) Create your `.env` file:**
```bash
cp .env.example .env
```

Edit `.env` and fill in your AWS credentials:
```
AWS_ACCESS_KEY_ID=your_access_key_id
AWS_SECRET_ACCESS_KEY=your_secret_access_key
AWS_DEFAULT_REGION=us-east-1
```

**b) Start Docker Desktop, then:**
```bash
cd llm_streamlit_demo
docker compose up --build
```

Open `http://localhost:8501`. Verify the container is running:
```bash
docker ps
```
Look for `0.0.0.0:8501->8501/tcp` in the PORTS column.

---

## Step 3 — Deploy to AWS EC2

### 3a — Create ECR repository

```bash
aws ecr create-repository --repository-name bedrock-chatbot --region us-east-1
```

### 3b — Build and push image to ECR

```bash
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin <ACCOUNT_ID>.dkr.ecr.us-east-1.amazonaws.com

docker build -t bedrock-chatbot ./app

docker tag bedrock-chatbot:latest <ACCOUNT_ID>.dkr.ecr.us-east-1.amazonaws.com/bedrock-chatbot:latest

docker push <ACCOUNT_ID>.dkr.ecr.us-east-1.amazonaws.com/bedrock-chatbot:latest
```

### 3c — Create IAM role for EC2

```bash
# Write trust policy
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

# Create role and attach permissions
aws iam create-role --role-name EC2BedrockRole --assume-role-policy-document file://ec2-trust.json
aws iam attach-role-policy --role-name EC2BedrockRole --policy-arn arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryReadOnly
aws iam attach-role-policy --role-name EC2BedrockRole --policy-arn arn:aws:iam::aws:policy/AmazonBedrockFullAccess

# Create and attach instance profile
aws iam create-instance-profile --instance-profile-name EC2BedrockProfile
aws iam add-role-to-instance-profile --instance-profile-name EC2BedrockProfile --role-name EC2BedrockRole
```

### 3d — Launch EC2 instance with UserData

```bash
aws ec2 run-instances --image-id ami-0c02fb55956c7d316 --instance-type t2.micro --region us-east-1 --iam-instance-profile Name=EC2BedrockProfile --user-data file://userdata.sh --tag-specifications "ResourceType=instance,Tags=[{Key=Name,Value=bedrock-chatbot}]" --query "Instances[0].InstanceId" --output text
```

### 3e — Open port 8501

```bash
# Get security group ID
aws ec2 describe-instances --instance-ids <INSTANCE_ID> --region us-east-1 --query "Reservations[0].Instances[0].SecurityGroups[0].GroupId" --output text

# Open port 8501
aws ec2 authorize-security-group-ingress --group-id <SG_ID> --protocol tcp --port 8501 --cidr 0.0.0.0/0 --region us-east-1
```

### 3f — Get public IP and open app

```bash
aws ec2 describe-instances --instance-ids <INSTANCE_ID> --region us-east-1 --query "Reservations[0].Instances[0].PublicIpAddress" --output text
```

Wait 3-4 minutes for UserData to complete, then open:
```
http://<PUBLIC_IP>:8501
```

### Instance management

```bash
# Stop when not in use (saves cost)
aws ec2 stop-instances --instance-ids <INSTANCE_ID> --region us-east-1

# Start again
aws ec2 start-instances --instance-ids <INSTANCE_ID> --region us-east-1
```

---

## Step 4 — CI/CD (GitHub Actions)

Every push to `main` automatically builds and redeploys to EC2.

**One-time setup — add these secrets to your GitHub repo** (`Settings → Secrets → Actions`):

| Secret | Value |
|---|---|
| `AWS_ACCESS_KEY_ID` | IAM deploy user access key |
| `AWS_SECRET_ACCESS_KEY` | IAM deploy user secret |
| `EC2_HOST` | EC2 public IP address |
| `EC2_SSH_KEY` | EC2 private key contents (PEM) |

Push to `main` and watch the Actions tab — the workflow builds the image, pushes to ECR, SSHs into EC2 and restarts the container automatically.

---

## Cost Reference

| Resource | Cost |
|---|---|
| Claude Sonnet 4.6 input | $3.00 / 1M tokens |
| Claude Sonnet 4.6 output | $15.00 / 1M tokens |
| EC2 t2.micro | Free tier (750 hrs/month) |
| ECR storage | $0.10 / GB / month |

A typical chat message costs ~$0.000050. Stop the EC2 instance when not in use to avoid charges.
