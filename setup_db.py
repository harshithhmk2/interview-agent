#!/usr/bin/env python3
import os
import sys
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

def load_env():
    """Simple parser to read environment variables from .env file if it exists."""
    env_vars = {}
    if os.path.exists(".env"):
        with open(".env", "r") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if "=" in line:
                    key, val = line.split("=", 1)
                    env_vars[key.strip()] = val.strip()
    return env_vars

def get_db_credentials():
    """Retrieve database credentials from environment or defaults."""
    env = load_env()
    
    # Check OS env first, then loaded .env, then fallback to defaults
    user = os.getenv("POSTGRES_USER") or env.get("POSTGRES_USER") or "postgres"
    password = os.getenv("POSTGRES_PASSWORD") or env.get("POSTGRES_PASSWORD") or "postgres_password"
    host = os.getenv("POSTGRES_HOST") or env.get("POSTGRES_HOST") or "localhost"
    port = os.getenv("POSTGRES_PORT") or env.get("POSTGRES_PORT") or "5432"
    db_name = os.getenv("POSTGRES_DB") or env.get("POSTGRES_DB") or "interview_db"
    
    return user, password, host, port, db_name

def create_database():
    """Connects to the default PostgreSQL server and creates the target database if it does not exist."""
    user, password, host, port, db_name = get_db_credentials()
    
    print(f"Connecting to PostgreSQL server at {host}:{port} as user '{user}'...")
    try:
        # Connect to default 'postgres' database first to perform database creation
        conn = psycopg2.connect(
            user=user,
            password=password,
            host=host,
            port=port,
            database="postgres"
        )
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cursor = conn.cursor()
        
        # Check if database already exists
        cursor.execute("SELECT 1 FROM pg_catalog.pg_database WHERE datname = %s;", (db_name,))
        exists = cursor.fetchone()
        
        if not exists:
            print(f"Database '{db_name}' does not exist. Creating...")
            cursor.execute(f'CREATE DATABASE "{db_name}";')
            print(f"Database '{db_name}' created successfully.")
        else:
            print(f"Database '{db_name}' already exists.")
            
        cursor.close()
        conn.close()
        
    except psycopg2.OperationalError as e:
        print("\n[ERROR] Unable to connect to the PostgreSQL server.")
        print("Please ensure that:")
        print("  1. The Docker container is running ('docker-compose up -d').")
        print("  2. The credentials in your .env file match your container configuration.")
        print(f"\nConnection Error Details:\n{e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n[ERROR] An unexpected error occurred: {e}")
        sys.exit(1)

def run_migrations():
    """Runs database migrations using Alembic if configured, or outputs instructions."""
    print("\n--- Database Migrations ---")
    if os.path.exists("alembic.ini") and os.path.exists("src/db/models.py"):
        print("Alembic is configured. Running migrations...")
        try:
            import subprocess
            result = subprocess.run(["alembic", "upgrade", "head"], capture_output=True, text=True)
            if result.returncode == 0:
                print("Migrations completed successfully.")
            else:
                print("[WARNING] Alembic migration failed:")
                print(result.stderr)
        except FileNotFoundError:
            print("[INFO] Alembic CLI not found in path. Please run 'poetry run alembic upgrade head' manually.")
    else:
        print("[INFO] Database structure will be created automatically by the FastAPI application")
        print("       upon startup using SQLAlchemy, or you can run migrations later once")
        print("       models and alembic are initialized.")
        
    print("\nDatabase setup complete!")

if __name__ == "__main__":
    print("=========================================")
    print(" AI Voice Interview Agent Database Setup")
    print("=========================================")
    create_database()
    run_migrations()
