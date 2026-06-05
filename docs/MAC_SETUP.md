# Mac Setup

## 1. Create a virtual environment

```bash
cd /path/to/Helix-Swarm
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

## 2. Start a local OpenAI-compatible model server

LM Studio default:

```text
http://localhost:1234/v1/chat/completions
```

Ollama OpenAI-compatible endpoint:

```text
http://localhost:11434/v1/chat/completions
```

Update `helix_config.json` or use environment variables:

```bash
export HELIX_ACTIVE=local
export HELIX_LOCAL_URL=http://localhost:1234/v1/chat/completions
export HELIX_LOCAL_MODEL=your-local-model-name
export HELIX_LOCAL_API_KEY=not-needed
```

## 3. Run

```bash
python cli.py
```

Use `/local` to switch to the local model profile, `/custom` to use a configured remote endpoint, and `/help` for commands.
