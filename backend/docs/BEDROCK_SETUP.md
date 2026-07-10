# EMBEDHUNT AI — AWS Bedrock Setup

How to provision Claude access on AWS Bedrock and wire it into EMBEDHUNT.

## 1. Get a `BEDROCK_API_KEY`

EMBEDHUNT uses the Anthropic Bedrock client with a **Bedrock API key** (bearer
token), passed to the SDK via `AWS_BEARER_TOKEN_BEDROCK`.

1. Sign in to the [AWS Console](https://console.aws.amazon.com/).
2. Go to **Amazon Bedrock → API keys** (or **IAM → Users** to create a
   programmatic user, see permissions below).
3. Generate a **long-term Bedrock API key**. Copy it once — it is not shown
   again.
4. Put it in `backend/.env`:

   ```
   BEDROCK_API_KEY=<your-key>
   AWS_REGION=us-east-1
   LLM_ENRICHMENT_ENABLED=true
   ```

## 2. Required IAM permissions

The identity behind the key needs, at minimum, invoke permissions on the Claude
models:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "BedrockInvokeClaude",
      "Effect": "Allow",
      "Action": [
        "bedrock:InvokeModel",
        "bedrock:InvokeModelWithResponseStream"
      ],
      "Resource": [
        "arn:aws:bedrock:*::foundation-model/anthropic.claude-*"
      ]
    },
    {
      "Sid": "BedrockListModels",
      "Effect": "Allow",
      "Action": ["bedrock:ListFoundationModels"],
      "Resource": "*"
    }
  ]
}
```

Scope `Resource` to your region/account in production.

## 3. Request Claude model access

Model access is off by default per account:

1. In Bedrock, open **Model access** (left nav).
2. Click **Manage model access / Enable specific models**.
3. Enable the Anthropic Claude models you route to:
   - Claude Haiku (extraction / summarization)
   - Claude Sonnet (mentoring / interview / matching / coding / salary / roadmap)
   - Claude Opus (complex reasoning)
4. Submit. Access is usually granted immediately for Anthropic models.
5. Ensure the model ids in `settings.py`
   (`LLM_HAIKU_MODEL`/`LLM_SONNET_MODEL`/`LLM_OPUS_MODEL`) match the enabled
   models in your region.

## 4. Test the connection

Quick smoke test from `backend/`:

```bash
python -c "import asyncio; from app.llm.bedrock_client import BedrockClient; \
from app.config.settings import settings; \
print(asyncio.run(BedrockClient().invoke_model(settings.LLM_HAIKU_MODEL, \
[{'role':'user','content':'ping'}], max_tokens=8)))"
```

Expected: a dict with `content`, `input_tokens`, `output_tokens` and a real
`model` id (not `"fallback"`).

If you get `"model": "fallback"` or a `BedrockError`:
- Confirm `BEDROCK_API_KEY` is set and valid.
- Confirm model access is granted in **this** `AWS_REGION`.
- Confirm the `anthropic` package is installed (`pip install anthropic`).
- Check the circuit breaker state via `GET /api/v1/ai/system/health` (admin).

To run entirely without Bedrock, set `LLM_ENRICHMENT_ENABLED=false` — the app
starts and all non-AI features work.
