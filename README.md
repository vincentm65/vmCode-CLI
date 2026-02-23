# vmCode

A terminal-based AI coding assistant powered by OpenAI-style function calling with tools for codebase search, file editing, and web search.

## Features

- **Multiple LLM Provider Support**: OpenAI, Anthropic, OpenRouter, GLM, Gemini, Kimi, MiniMax, and local models
- **Tool-Based Interaction**: Code search (`rg`), file editing, directory operations, and web search
- **Multiple Modes**: Edit (full access), Plan (read-only), and Learn (documentation style)
- **Parallel Execution**: Run multiple tools concurrently for efficiency
- **Conversation History**: Markdown logging with context compaction
- **Approval Workflows**: Safety checks for dangerous commands

## Installation

### Option 1: npm install (Recommended)

```bash
# Install globally (requires Python 3.9+)
npm install -g vmcode

# Run vmcode
vmcode
```

Or use npx without installing:

```bash
npx vmcode
```

### What Gets Installed

The npm package automatically:
1. Checks for Python 3.9+ on your system
2. Installs Python dependencies via pip
3. Creates `config.yaml` from `config.yaml.example` if missing
4. Sets up the `vmcode` command globally

**Requirements:**
- Node.js 14+ (for npm)
- Python 3.9+ (for the application)
- pip (to install Python dependencies)

If Python is not found, the installer will guide you through installing it.

### Option 2: Git Clone

```bash
# Clone the repository
git clone <repository-url>
cd vmcode

# Run setup script
./setup.sh          # Linux/macOS
# or
setup.bat           # Windows
```

The setup script automatically:
1. Checks for Python 3.9+ on your system
2. Installs Python dependencies via pip
3. Creates `config.yaml` from `config.yaml.example` if missing
4. Sets up the `vmcode` command alias

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

Edit `config.yaml` in the project root and add your keys:

```yaml
# OpenAI
OPENAI_API_KEY: "sk-your-key-here"
OPENAI_MODEL: gpt-4o-mini

# Anthropic (Claude)
ANTHROPIC_API_KEY: "sk-ant-your-key-here"
ANTHROPIC_MODEL: claude-3-5-sonnet-20241022

# Or any other supported provider...
```

**Note:** `config.yaml` is automatically created from `config.yaml.example` on first run and is in `.gitignore` to protect your secrets.

#### Option 3: Environment Variables

Set environment variables (they take precedence over config.yaml):

```bash
export OPENAI_API_KEY="sk-your-key-here"
export ANTHROPIC_API_KEY="sk-ant-your-key-here"

vmcode
```

### Available Environment Variables

- `ANTHROPIC_API_KEY` - Anthropic (Claude) API key
- `OPENAI_API_KEY` - OpenAI API key
- `GLM_API_KEY` - GLM (Zhipu AI) API key
- `GEMINI_API_KEY` - Google Gemini API key
- `OPENROUTER_API_KEY` - OpenRouter API key
- `KIMI_API_KEY` - Kimi (Moonshot AI) API key
- `MINIMAX_API_KEY` - MiniMax API key

## Commands

- `/provider <name>` - Switch LLM provider
- `/model <name>` - Set model for current provider
- `/key <api_key>` - Set API key for current provider
- `/mode <edit|plan|learn>` - Switch interaction mode
- `/config` - Show all configuration settings
- `/help` - Display all available commands

## Project Structure

```
vmcode/
├── bin/
│   └── npm-wrapper.js   # npm entry point
├── scripts/
│   └── install.js       # npm post-install script
├── config.yaml.example   # Configuration template (committed)
├── config.yaml         # Your API keys and settings (not in git)
├── requirements.txt     # Python dependencies
├── package.json        # npm package definition
├── setup.sh            # Git clone setup script (Linux/macOS)
├── setup.bat           # Git clone setup script (Windows)
├── .npmignore          # npm package exclusions
├── .gitignore          # git exclusions
├── src/
│   ├── core/           # Core orchestration and state management
│   ├── llm/            # LLM client and provider configurations
│   ├── ui/             # CLI interface and commands
│   └── utils/          # Utilities (file ops, search, validation)
└── tests/              # Test suite (to be implemented)
```

## Security

- `config.yaml` is excluded from git via `.gitignore`
- Never commit API keys or sensitive configuration
- Use environment variables for CI/CD or shared environments

## Development

vmCode is currently in active development. Production readiness is in progress with focus on:
- Comprehensive test coverage
- Documentation
- Error handling improvements
- Performance optimizations

## Publishing to npm

To publish vmCode to the npm registry:

1. **Update package.json** with your details:
   ```json
   {
     "name": "vmcode",
     "author": "Your Name <email>",
     "repository": {
       "url": "https://github.com/yourusername/vmcode.git"
     },
     "homepage": "https://github.com/yourusername/vmcode"
   }
   ```

2. **Test locally**:
   ```bash
   npm pack
   npm install -g vmcode-0.1.0.tgz
   vmcode
   npm uninstall -g vmcode
   ```

3. **Publish**:
   ```bash
   npm login
   npm publish
   ```

For scoped packages (e.g., `@yourusername/vmcode`):
   ```bash
   npm publish --access public
   ```

## License

[Your License Here]
