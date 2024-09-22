# Setting up the project

## Installing Tools, Environment, Dependencies

We're using `pyenv` to manage `Python` versions and `poetry` to manage dependencies and
the virtual environment on the host machine. We're using `pipx` to install `poetry`.

### Installing `pyenv`

```bash
curl https://pyenv.run | bash
echo 'export PYENV_ROOT="$HOME/.pyenv"' >> ~/.bashrc
echo 'command -v pyenv >/dev/null || export PATH="$PYENV_ROOT/bin:$PATH"' >> ~/.bashrc
echo 'eval "$(pyenv init -)"' >> ~/.bashrc
```

### Installing `pipx`

```bash
sudo apt update
sudo apt install pipx
pipx ensurepath
```

### Installing `poetry`

```bash
pipx install poetry
poetry completions bash >> ~/.bash_completion
```

### Check `PATH`

After installing the tools restart your shell.

Check if everything installed successfully:

```shell
which pyenv
pyenv --version
which poetry
pyenv --version
```

### Installing Python

```shell
pyenv install 3.12
pyenv local 3.12.6  # specify the version just installed
```

### Installing Dependencies

```shell
poetry install
poetry env use 3.12  # using the correct `Python` interpreter
poetry env info  # checking if correct environment is set
poetry show  # list installed packages
```

Relaunch the terminal.

Finally set the correct python interpreter in your `IDE` based on output from `poetry env info`.

Without using `Docker` you can use `poetry run python src/main.py` as an entrypoint.

### **Optional:** Install And Use `pre-commit`

```bash
pre-commit install --install-hooks
# will check staged files against `pre-commit` hooks defined in `.pre-commit-config.yaml
pre-commit run
```

### Getting The Data

Scraping of the full dataset takes pretty long. We don't want to strain the server unnecessarily:

[Download matchreports](https://drive.google.com/drive/folders/1M2-xkV0-wgnaMoJMP4Jg6XpfW_kAsMQp?usp=sharing).

Extract them in project folder to be recognized by the scraper.
