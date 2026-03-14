### Setup Guide `v 0.1.0`
the-bible-catalog
___ 

> **Purpose**
>
>This document provides complete setup instructions for Mac users to get started with the Bible Catalog project, including environment configuration, dependency installation, and troubleshooting common issues.

### Contents
- [Prerequisites](#prerequisites)
- [Quick Start](#quick-start)
  - [Step 1: Install Homebrew](#step-1-install-homebrew)
  - [Step 2: Clone the Repository](#step-2-clone-the-repository)
  - [Step 3: Install System Dependencies](#step-3-install-system-dependencies)
  - [Step 4: Create Virtual Environment with Python 3.12](#step-4-create-virtual-environment-with-python-312)
  - [Step 5: Install Python Dependencies](#step-5-install-python-dependencies)
  - [Step 6: Configure Environment Variables](#step-6-configure-environment-variables)
  - [Step 7: Launch JupyterLab](#step-7-launch-jupyterlab)
- [Working with Notebooks](#working-with-notebooks)
  - [Select the Correct Kernel](#select-the-correct-kernel)
- [Installing Dependencies from a Notebook](#installing-dependencies-from-a-notebook)
  - [Method 1: Using the Virtual Environment Python (Recommended)](#method-1-using-the-virtual-environment-python-recommended)
  - [Method 2: Using Current Kernel (Simpler)](#method-2-using-current-kernel-simpler)
- [Project Dependencies](#project-dependencies)
- [Troubleshooting](#troubleshooting)
  - [Issue: "externally-managed-environment" error](#issue-externally-managed-environment-error)
  - [Issue: Python 3.14 compatibility error](#issue-python-314-compatibility-error)
  - [Issue: Wrong Python version in notebook](#issue-wrong-python-version-in-notebook)
  - [Issue: Module not found errors](#issue-module-not-found-errors)
- [Daily Workflow](#daily-workflow)
  - [Starting a Work Session](#starting-a-work-session)
  - [Ending a Work Session](#ending-a-work-session)
- [Additional Resources](#additional-resources)
  - [Git Integration in JupyterLab](#git-integration-in-jupyterlab)
  - [Updating Dependencies](#updating-dependencies)
- [Project Structure](#project-structure)
- [Verification Checklist](#verification-checklist)
- [Pro Tips](#pro-tips)
- [Getting Help](#getting-help)
- [Summary](#summary)

### Prerequisites

*   **Mac** (macOS 11+)
*   **Homebrew** (if not installed, see below)

### Quick Start

#### Step 1: Install Homebrew

If not already installed:

```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

After installation, follow the terminal instructions to add Homebrew to your PATH.

#### Step 2: Clone the Repository

```bash
cd ~/Github  # or wherever you keep your projects
git clone https://github.com/yourusername/the-bible-catalog.git
cd the-bible-catalog
```

#### Step 3: Install System Dependencies

```bash
# Install Python 3.12 (required for compatibility with all dependencies)
brew install python@3.12

# Install Node.js (required for JupyterLab extensions)
brew install node
```

#### Step 4: Create Virtual Environment with Python 3.12

⚠️ **Important:** This project requires Python 3.12 for dependency compatibility.

```bash
# Navigate to project directory
cd ~/Github/the-bible-catalog

# Create .venv
/opt/homebrew/opt/python@3.12/bin/python3.12 -m venv .venv

# Activate the virtual environment
source .venv/bin/activate

# Verify you're using Python 3.12
python --version  # Should show: Python 3.12.x
```

💡 **Tip:** You'll need to activate this virtual environment every time you work on the project:

```bash
source ~/Github/the-bible-catalog/.venv/bin/activate
```

#### Step 5: Install Python Dependencies

With the virtual environment activated:

```bash
# Upgrade pip first
pip install --upgrade pip

# Install JupyterLab and Git extension
pip install jupyterlab jupyterlab-git

# Register the virtual environment as a Jupyter kernel
python -m ipykernel install --user --name=bible-catalog --display-name="Python 3.12 (bible-catalog)"

# Install project dependencies
pip install -r requirements.txt
```

#### Step 6: Configure Environment Variables

Create a `.env` file in the `config` directory:

```bash
# Create config directory if it doesn't exist
mkdir -p config

# Create .env file
touch config/.env
```

Edit `config/.env` with your configuration:

```bash
# Example .env content
OPENAI_API_KEY=your_openai_key_here
ANTHROPIC_API_KEY=your_anthropic_key_here
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=your_password_here
# Add other environment variables as needed
```

#### Step 7: Launch JupyterLab

```bash
# Make sure virtual environment is activated
source .venv/bin/activate

# Start JupyterLab
jupyter lab
```

JupyterLab will open in your browser automatically.

### Working with Notebooks

#### Select the Correct Kernel

When you open a notebook in JupyterLab:

1. Click **Kernel** → **Change Kernel**
2. Select **"Python 3.12 (bible-catalog)"**

This ensures your notebooks use the virtual environment with all dependencies installed.

### Installing Dependencies from a Notebook

If you need to install dependencies while working in a Jupyter notebook:

#### Method 1: Using the Virtual Environment Python (Recommended)

```python
import sys
from pathlib import Path

def find_project_root():
    """Find the project root directory."""
    current = Path().resolve()
    
    project_indicators = [
        "requirements.txt",
        "pyproject.toml", 
        ".git",
        "config/.env",
        "the-bible-catalog"
    ]
    
    for parent in [current] + list(current.parents):
        for indicator in project_indicators:
            if (parent / indicator).exists():
                return parent
    return current

# Find project root
PROJECT_ROOT = find_project_root()
requirements_path = PROJECT_ROOT / "requirements.txt"

# Use the virtual environment's Python to install
venv_python = PROJECT_ROOT / ".venv/bin/python"
!{venv_python} -m pip install -r {requirements_path}
```

#### Method 2: Using Current Kernel (Simpler)

If you're already using the correct kernel:

```python
import sys
from pathlib import Path

def find_project_root():
    current = Path().resolve()
    project_indicators = ["requirements.txt", ".git", "the-bible-catalog"]
    for parent in [current] + list(current.parents):
        for indicator in project_indicators:
            if (parent / indicator).exists():
                return parent
    return current

PROJECT_ROOT = find_project_root()
requirements_path = PROJECT_ROOT / "requirements.txt"

# Install using current kernel's Python
!{sys.executable} -m pip install -r {requirements_path}
```

### Project Dependencies

The `requirements.txt` includes:

```
duckdb>=0.9.0           # Relational database (Bronze/Silver layers)
neo4j>=5.0.0            # Graph database (Gold layer)
pandas>=1.5.0           # Data manipulation
sentence-transformers>=2.2.0  # Embeddings
openai>=1.0.0           # OpenAI API
anthropic>=0.8.0        # Anthropic API
langchain>=0.1.0        # LLM framework
pinecone-client>=2.0.0  # Vector database
beautifulsoup4>=4.12.0  # HTML parsing
python-dotenv           # Environment variables
requests                # HTTP requests
pypdf                   # PDF processing
jupyter                 # Jupyter notebooks
ipykernel               # Jupyter kernel
```

### Troubleshooting

#### Issue: "externally-managed-environment" error

**Problem:**

```
error: externally-managed-environment
× This environment is externally managed
```

**Solution:**

Use a virtual environment (already covered in Step 4). Never install packages system-wide with `--break-system-packages`.

#### Issue: Python 3.14 compatibility error

**Problem:**

```
RuntimeError: Cannot install on Python version 3.14.0; only versions >=3.10,<3.14 are supported.
```

**Solution:**

Use Python 3.12 (already covered in Step 4).

#### Issue: Wrong Python version in notebook

**Problem:**

Notebook is using the wrong Python version.

**Solution:**

1. Click **Kernel** → **Change Kernel**
2. Select **"Python 3.12 (bible-catalog)"**
3. If not available, re-register the kernel:

```bash
source ~/Github/the-bible-catalog/.venv/bin/activate
python -m ipykernel install --user --name=bible-catalog --display-name="Python 3.12 (bible-catalog)"
```

#### Issue: Module not found errors

**Problem:**

```
ModuleNotFoundError: No module named 'duckdb'
```

**Solution:**

1. Make sure your virtual environment is activated:

```bash
source ~/Github/the-bible-catalog/.venv/bin/activate
```

2. Reinstall dependencies:

```bash
pip install -r requirements.txt
```

3. In notebooks, make sure you're using the "Python 3.12 (bible-catalog)" kernel

### Daily Workflow

#### Starting a Work Session

```bash
# 1. Navigate to project
cd ~/Github/the-bible-catalog

# 2. Activate virtual environment
source .venv/bin/activate

# 3. Start JupyterLab
jupyter lab
```

#### Ending a Work Session

```bash
# 1. Stop JupyterLab (Ctrl+C in terminal)

# 2. Deactivate virtual environment
deactivate
```

### Additional Resources

#### Git Integration in JupyterLab

The `jupyterlab-git` extension provides a visual interface for Git operations:

*   View changes in the left sidebar (Git icon)
*   Stage/unstage files
*   Commit changes
*   Push/pull from remote
*   View commit history

#### Updating Dependencies

To update all dependencies to their latest compatible versions:

```bash
# Activate virtual environment
source .venv/bin/activate

# Update packages
pip install --upgrade -r requirements.txt
```

To update a specific package:

```bash
pip install --upgrade package-name
```

### Project Structure

```
the-bible-catalog/
├── config/             # Configuration files
│   └── .env            # Environment variables (create this)
├── database/
│   └── setup/          # Database setup scripts and notebooks
├── docs/               # Documentation
├── notebooks/          # Jupyter notebooks
├── tests/              # Unit tests
├── .venv/              # Virtual environment (created in setup)
├── requirements.txt    # Python dependencies
└── README.md           # Project overview
```

### Verification Checklist

After setup, verify everything works:

*   Python 3.12 is being used: `python --version`
*   Virtual environment activates: `source .venv/bin/activate`
*   JupyterLab starts: `jupyter lab`
*   "Python 3.12 (bible-catalog)" kernel is available in notebooks
*   Node.js is installed: `node --version`
*   Can import project modules in notebooks

### Pro Tips

1. **Add virtual environment activation to your shell profile** for convenience:

```bash
echo 'alias biblecatalog="cd ~/Github/the-bible-catalog && source .venv/bin/activate"' >> ~/.zshrc
source ~/.zshrc
```

Now just type `biblecatalog` to navigate and activate!

2. **Use VS Code with Jupyter extension** as an alternative to JupyterLab:
   *   Install VS Code
   *   Install Python extension
   *   Select "Python 3.12 (bible-catalog)" as interpreter

3. **Keep your virtual environment updated**:

```bash
pip list --outdated  # See which packages have updates
```

### Getting Help

If you encounter issues not covered here:

1. Check the error message carefully
2. Verify virtual environment is activated
3. Confirm you're using the correct Jupyter kernel
4. Try reinstalling dependencies: `pip install -r requirements.txt --force-reinstall`
5. Create an issue on GitHub with error details

### Summary

**One-time setup:**

1. Install Homebrew, Python 3.12, Node.js
2. Create virtual environment with Python 3.12
3. Install dependencies
4. Register Jupyter kernel
5. Configure environment variables

**Every work session:**

1. Activate virtual environment: `source .venv/bin/activate`
2. Start JupyterLab: `jupyter lab`
3. Select "Python 3.12 (bible-catalog)" kernel in notebooks

That's it! You're ready to work with the Bible Catalog project. 🎉
