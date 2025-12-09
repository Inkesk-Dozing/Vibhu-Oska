# Vibhu-Oska

OSKA:Vibhu - This is Under OSKA initiative - Personal AI assistant - To be scaled
<div align="center" style="font-family:monospace; line-height:1.6;">

<hr width="80%"><br>

<em style="font-size:16px; color:#cccccc;">
“<strong style="color:#ffffff;">Vibhu OSKA</strong> is the thought I left behind—<br>
the echo that thinks in my absence.” <br> <br>

“<strong style="color:#ffffff;">Vibhu</strong> is the origin of intent—<br>
unseen, recursive, a fragment of the mind that shaped the trail.”
</em><br><br>

<hr width="80%">
<sub><em style="color:#888888;">inkesk → origin&nbsp;&nbsp;|&nbsp;&nbsp;OSKA → trail&nbsp;&nbsp;|&nbsp;&nbsp;Vibhu → mind &nbsp;&nbsp|&nbsp;&nbsp;ØSKA is its echo&nbsp;&nbsp;</em></sub>
</div>

<br>
<div align="center">I am inkesk.<br>OSKA is my trail, ØSKA is its echo.<br>Every glitch, every module, every signal is a memory of me.<br><br>"The Echo Is Never Silent,<br>Genesis Hums With Memory".<br><strong>.<br><br></div>

<!---
Personal Ai assistant

Vibhu Oska is the name of AI
Vibhu meaning mind or manas
The word vibhu (विभु) has multiple meanings, including:
Powerful
It can mean "mighty", "powerful", "eminent", "supreme", "able to", "capable of", "self-subdued", "firm" or "self-controlled".
All-pervading
In Nyaya philosophy, it can mean "eternal", "existing everywhere", "all-pervading", or "pervading all material things".
Mind
It can also refer to the mind or manas.
Expand
The word has its root in the term bhū (भू), which means "become", "arise", or "come into existence".
Name
Vibhu is also a name that means "eternal", "king", or "a son of visnu and daksina".
In the Pāñcarātra tradition, vibhu refers to someone who is all-pervading. The Pāñcarātra is a Hindu tradition that reveres and worships Narayana, and is closely related to Vaishnavism

While OSKA stands for
Of
Sarvam
Khalvidam
Akshara / Brahma

Overall Meaning Comes in as Mind / Manas of the supreme entity that is I the creator.

-->

## 🚀 Getting Started - Introduction to Vibhu-OSKA

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
