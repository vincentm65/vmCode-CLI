# vmCode Installation Methods

## Summary

vmCode now supports **two installation methods**:

1. **npm install** - Recommended, easiest
2. **Git clone + setup script** - For development/contributors

Both methods result in a `vmcode` command you can run from anywhere.

---

## Method 1: npm install (Recommended)

```bash
npm install -g vmcode-cli
vmcode
```

**What happens:**
- Downloads package from npm
- Runs `scripts/install.js` post-install
- Checks for Python 3.9+
- Installs Python dependencies via pip
- Creates `config.yaml` from example
- Sets up global `vmcode` command

**Requirements:**
- Node.js 14+
- Python 3.9+
- pip

**Files used:**
- `package.json` - npm package definition
- `bin/npm-wrapper.js` - entry point
- `scripts/install.js` - post-install script
- `.npmignore` - controls what's published

---

## Method 2: Git Clone + Setup

```bash
git clone <repository-url>
cd vmcode
./setup.sh          # Linux/macOS
# or
setup.bat           # Windows
```

**What happens:**
- Checks for Python 3.9+
- Installs Python dependencies via pip
- Creates `config.yaml` from example
- Creates `vmcode` command in `~/.local/bin/` (Linux/macOS) or `%USERPROFILE%\bin` (Windows)
- Adds to PATH (or shows instructions)

**Requirements:**
- Python 3.9+
- pip

**Files used:**
- `setup.sh` - Linux/macOS setup script
- `setup.bat` - Windows setup script

---

## How the Git Clone Setup Works

### Linux/macOS (`setup.sh`)

1. Creates `~/.local/bin/vmcode` script
2. Makes it executable
3. Checks if `~/.local/bin` is in PATH
4. If not in PATH, shows instructions to add to `~/.bashrc` or `~/.zshrc`

### Windows (`setup.bat`)

1. Creates `%USERPROFILE%\bin\vmcode.bat` batch file
2. Checks if `%USERPROFILE%\bin` is in PATH
3. If not in PATH, shows GUI instructions to add to Environment Variables

---

## Files Summary

### npm Installation
```
bin/npm-wrapper.js       # npm entry point (launches Python)
scripts/install.js       # npm post-install (installs deps)
package.json            # npm package definition
.npmignore              # npm package exclusions
```

### Git Clone Installation
```
setup.sh                # Linux/macOS setup
setup.bat               # Windows setup
```

### Shared (Both methods)
```
config.yaml.example       # Configuration template
requirements.txt         # Python dependencies
src/                    # Python application
.gitignore              # Protects config.yaml
```

---

## Comparison

| Feature | npm | Git Clone |
|---------|-----|------------|
| Easiest | ✅ | ❌ |
| Auto-deps | ✅ | ✅ |
| Auto-config | ✅ | ✅ |
| Auto-command | ✅ | ✅ |
| No npm required | ❌ | ✅ |
| For contributors | ❌ | ✅ |
| Published to registry | ✅ | ❌ |

---

## Choosing a Method

**Use npm if:**
- You want the easiest installation
- You don't need to modify the code
- You're an end user

**Use git clone if:**
- You want to contribute
- You need to modify the code
- You don't have npm installed
- You're developing vmCode

---

## Troubleshooting

### "vmcode: command not found" (npm)
```bash
# Check npm global location
npm config get prefix

# Add to PATH (example for Linux/macOS)
export PATH="$(npm config get prefix)/bin:$PATH"
```

### "vmcode: command not found" (git clone)
```bash
# For Linux/macOS
export PATH="$HOME/.local/bin:$PATH"
# Then reload shell
source ~/.bashrc  # or ~/.zshrc
```

### "Python not found"
- Install Python 3.9+ from https://python.org
- Make sure it's in your PATH

---

## Uninstallation

### npm
```bash
npm uninstall -g vmcode-cli
```

### Git Clone
```bash
# Remove the command
rm ~/.local/bin/vmcode        # Linux/macOS
rm %USERPROFILE%\bin\vmcode.bat  # Windows

# Remove the project
rm -rf vmcode
```
