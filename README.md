# Setting up the project

## Installing Tools And Dependencies

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

## Environment Files And Variables

### Primary `.env` File

Docker will use the appropriate ´.env´ file base on the environment variable defined in the ´.env´ file:

- `ACTIVE_ENV`: Specifies the active environment configuration file (e.g., `.env.dev`, `.env.prod`).

Possible names for environments are as follows:

- ´.env.dev´: Used for development.
- ´.env.test´: Used for testing.
- ´.env.prod: Used in production.

Using ´Pydantic´ settings environment variables are selected automatically based on the presence of an ´.env´ file of those specific names. If several are found the precedence is ´prod´, ´test´, ´dev´.

You might need to create and adapt the ´.env´ files, especially for production.

### Environment-Specific Files (`.env.dev`, `.env.prod`, etc.)

- `PYTHONDONTWRITEBYTECODE`: Set to `1` to prevent Python from writing `.pyc` files.
- `PYTHONPATH`: Specifies the Python path.
- `LOGGING_ENV`: Logging environment (`dev`, `prod`, etc.).
- `POSTGRES_USER`: Database username.
- `POSTGRES_PASSWORD`: Database password.
- `POSTGRES_DB`: Database name.
- `SYNC_URL`: Synchronous database connection URL.
- `ASYNC_URL`: Asynchronous database connection URL.
- `SCRAPER_INTERVAL`: Interval for the scraper in seconds.

## Getting The Data Without Actually Scraping

Scraping of the full dataset takes pretty long. We don't want to strain the server unnecessarily:

[Download Match Reports](https://drive.google.com/drive/folders/1M2-xkV0-wgnaMoJMP4Jg6XpfW_kAsMQp?usp=sharing).

Extract them in project folder to be recognized by the scraper.

## Using Docker

To start the docker services (including for instance the database) run: ´docker-compose --env-file .env.dev up -d --build´ explicitely specifying which ´.env´ file to be used. if you want to reinitialize (=delete)all mounted volumes call ´docker compose down -v´.

In production you need to run

- ´docker build -t scraper-image -f src/scraper/Dockerfile .´
- ´docker build -t web-image -f src/scraper/Dockerfile .´
- ´docker-compose --env-file .env.prod -f docker-compose.yml up -d --build´.

To stop docker services run ´docker compose down´.
