param(
    [string]$EnvFile = ".env"
)

$env:ENV_FILE = $EnvFile
python bot.py
