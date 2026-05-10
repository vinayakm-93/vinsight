# Miscellaneous Utility Scripts

This folder contains standalone Python scripts that are useful for database administration, environment seeding, and system verification. They are kept here to avoid cluttering the repository root while remaining accessible for future use.

## Database & Admin Utilities
- **`seed_db.py`**: General script to seed the database with initial records or demo data.
- **`seed_users.py` / `seed_test_user.py`**: Scripts to quickly populate the database with test user accounts.
- **`reset_password.py`**: Admin utility to manually reset a user's password in the database.
- **`install_pgvector.py`**: Initialization script to set up `pgvector` extensions on a PostgreSQL instance.
- **`universal_migrate.py`**: Utility for running migrations or transitioning schemas across different database setups.
- **`check_holders.py`**: Checks or validates institutional holders data against the database.

## System Verification & Analysis
- **`verify_cloud_endpoints.py`**: Pings and verifies that the deployed Cloud Run endpoints are responsive and healthy.
- **`verify_data_endpoints.py`**: Validates the health and responses of the external data provider APIs (e.g., Finnhub, EODHD).
- **`verify_fixes.py`**: General verification script used to confirm bug fixes across different application modules.
- **`verify_optimization.py`**: Benchmarks or tests specific optimizations (likely the RAG / LLM response pipelines).
- **`summarize_earnings.py`**: A standalone utility script to pull and summarize earnings call transcripts.
- **`list_models.py`**: Utility to list available LLM models (e.g., from Gemini, Groq, or OpenAI) for testing routing capabilities.
