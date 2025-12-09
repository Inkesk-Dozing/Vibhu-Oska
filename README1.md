# Introduction to Vibhu-OSKA

## 🚀 Getting Started

### Prerequisites

- Python 3.10+
- Protocol Buffer Compiler (protoc)
- Redis (for OptimizationCore - optional)

### Installation

#### Clone the repository

Install dependencies:

```bash
pip install -r requirements.txt
```

#### Create a new Void (Virtual Environment)

You have to create a venv because (the new computer might be Linux while your old one was Windows.
You cannot share venvs between computers.)Jokes apart it will be helpful in-order,
*not to interfere with the in-built path of python* files.

```Bash

python -m venv venv-name
```

#### Activate it

```Bash

source venv-name/Scripts/activate
```

#### Regenerate the Artifacts

Running this command reads your pyproject.toml, downloads all the libraries, and automatically generates .egg-info folder for you on the new machine.

```Bash

pip install -e .
```

Compile Protos (Protocols):

```bash
./scripts/generate_code.sh
```

Run the Entry Point:

```bash
python Backend/EntryPoint.py
```

## 🤝 Contributing

Please refer to CONTRIBUTING.md for style guides regarding Core separation.

**Rules of Thumb:**

- Do not put business logic in the OrchestratorCore.
- Do not put database connections in CognitionCore.
- Keep BackupCore lightweight and dependency-free.
