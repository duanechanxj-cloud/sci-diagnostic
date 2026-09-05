# Start Here on macOS — V2.5.2

1. Open this project folder in VS Code.
2. Create/activate a project virtual environment.
3. Install requirements: `python -m pip install -r requirements.txt`.
4. Generate the Teacher/Admin password hashes: `python scripts/hash_password.py`.
5. Copy `.streamlit/secrets.example.toml` to `.streamlit/secrets.toml` and paste the generated hashes.
6. For local development, keep `persistence.enabled = false` unless you intentionally want hosted-state testing.
7. Run tests: `python -m pytest -q` (expected: 71 passed).
8. Start the app: `python -m streamlit run app/streamlit_app.py`.

For online deployment, follow `DEPLOYMENT_V2_5_2.md`.
