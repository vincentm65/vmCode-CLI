## bone-agent

A CLI-based AI coding assistant capable of codebase search, file editing, computer use, and web search.

<img width="1850" height="396" alt="image" src="https://github.com/user-attachments/assets/4f20cc22-a7d9-4423-afbf-15bbe1e29890" />

## Features

- **Multiple LLM Provider Support**: bone-agent (built-in proxy), OpenAI, Anthropic, OpenRouter, GLM, Gemini, Kimi, MiniMax, and local models
- **Tool-Based Interaction**: Code search (`rg`), file editing, directory operations, and web search
- **Multiple Modes**: Edit (full access), Plan (read-only), and Learn (documentation style)
- **Parallel Execution**: Run multiple tools concurrently for efficiency
- **Conversation History**: Markdown logging with context compaction
- **Approval Workflows**: Safety checks for dangerous commands

## Installation

### Option 1: npm install (Recommended)

```bash
# Install globally (requires Python 3.9+)
npm install -g bone-agent-cli

# Run bone-agent
bone-agent
```

Or use npx without installing:

```bash
npx bone-agent-cli
```

### What Gets Installed

The npm package automatically:
1. Checks for Python 3.9+ on your system
2. Installs Python dependencies via pip
3. Creates `~/.bone/config.yaml` from `config.yaml.example` if missing (persists across updates)
4. Sets up the `bone-agent` command globally

**Requirements:**
- Node.js 14+ (for npm)
- Python 3.9+ (for the application)
- pip (to install Python dependencies)

If Python is not found, the installer will guide you through installing it.

### Option 2: Git Clone

```bash
# Clone the repository
git clone https://github.com/vincentm65/bone-agent.git
cd bone-agent

# Install Python dependencies
pip install -r requirements.txt

# Run bone-agent
python src/ui/main.py
```

**Requirements:**
- Python 3.9+
- pip (to install Python dependencies)

## Configuration

### Setting API Keys

You have three options to set your API keys:

#### Option 1: Interactive Commands (Recommended)

Run the app and use the built-in commands:
```
> /key sk-your-api-key-here
> /provider openai
```

#### Option 2: Edit config.yaml Directly

Edit `~/.bone/config.yaml` and add your keys:

```yaml
# OpenAI
OPENAI_API_KEY: "sk-your-key-here"
OPENAI_MODEL: gpt-4o-mini

# Anthropic (Claude)
ANTHROPIC_API_KEY: "sk-ant-your-key-here"
ANTHROPIC_MODEL: claude-3-5-sonnet-20241022

# Or any other supported provider...
```

**Note:** Config is stored at `~/.bone/config.yaml` — it persists across npm updates and is never tracked by git.

#### Option 3: Environment Variables

Set environment variables (they take precedence over ~/.bone/config.yaml):

```bash
export OPENAI_API_KEY="sk-your-key-here"
export ANTHROPIC_API_KEY="sk-ant-your-key-here"

bone-agent
```

### Available Environment Variables

- `ANTHROPIC_API_KEY` - Anthropic (Claude) API key
- `OPENAI_API_KEY` - OpenAI API key
- `GLM_API_KEY` - GLM (Zhipu AI) API key
- `GEMINI_API_KEY` - Google Gemini API key
- `OPENROUTER_API_KEY` - OpenRouter API key
- `KIMI_API_KEY` - Kimi (Moonshot AI) API key
- `MINIMAX_API_KEY` - MiniMax API key
- `BONE_API_KEY` - bone-agent (proxy) API key (auto-set via `/signup`)
- `BONE_API_BASE` - bone-agent (proxy) API base URL (default: `https://api.vmcode.dev`)

## Commands

- `/provider <name>` - Switch LLM provider
- `/model <name>` - Set model for current provider
- `/key <api_key>` - Set API key for current provider
- `/mode <edit|plan|learn>` - Switch interaction mode
- `/config` - Show all configuration settings
- `/signup <email>` - Create a bone-agent account and get API key
- `/account` - View your bone-agent account and plan details
- `/plan` - View available plans and pricing
- `/upgrade` - Upgrade your subscription
- `/help` - Display all available commands

/help Menu:
<img width="1843" height="1349" alt="image" src="https://github.com/user-attachments/assets/631ab805-f012-4bb6-a031-c82a339e94c5" />


## Project Structure

```
bone-agent/
├── bin/
│   ├── npm-wrapper.js  # npm entry point
│   ├── rg              # ripgrep binary (Linux/macOS)
│   └── rg.exe          # ripgrep binary (Windows)
├── config.yaml.example # Configuration template
├── requirements.txt    # Python dependencies
├── package.json        # npm package definition
├── .npmignore          # npm package exclusions
├── .gitignore          # git exclusions
├── src/
│   ├── core/           # Core orchestration and state management
│   ├── llm/            # LLM client and provider configurations
│   ├── ui/             # CLI interface and commands
│   └── utils/          # Utilities (file ops, search, validation)
└── tests/              # Test suite (for development)
```

## bone-agent Plan (Built-in Proxy)

bone-agent offers a built-in proxy provider for a seamless setup experience. Create an account and start coding without configuring third-party API keys.

```
> /signup you@example.com
```

Available plans: **Free**, **Lite**, and **Pro**. Use `/plan` to see details and `/upgrade` to change plans.

*Paid plans coming soon.*

## Security

- User config lives at `~/.bone/config.yaml` — outside the repo and git, persists across updates
- Never commit API keys or sensitive configuration
- Use environment variables for CI/CD or shared environments

## Development

bone-agent is currently in active development. Production readiness is in progress with focus on:
- Comprehensive test coverage
- Documentation
- Error handling improvements
- Performance optimizations
