# Initialize project environment
import sys; sys.path.insert(0, next((str(p) for p in __import__('pathlib').Path.cwd().parents if (p/'config').exists()), '.'))

from config.settings import *

# Import common libraries
from config._common_libraries import *

def get_env(global_env=None):
    """
    Gets the environment (dev, ua, prod).
    1. Checks for the deployment-specific 'global_env' (e.g., from GitHub Actions).
    2. Fallbacks to the local OS/loaded ENVIRONMENT variable.
    3. Defaults to 'dev'.
    """
    # 1. Check for deployment-specific variable
    if global_env in VALID_ENVS:
        # This is likely what's being passed in CI/CD and overriding your local
        return global_env

    # 2. Check for local machine-specific environment variable (loaded from .env)
    # Uses the ENVIRONMENT variable determined in Section 4.
    if ENVIRONMENT in VALID_ENVS:
        return ENVIRONMENT.lower()

    # 3. Default (Should only happen if ENVIRONMENT was set to an invalid value)
    print("Warning: Environment not explicitly set. Defaulting to 'dev'.")
    return 'dev'
        
def get_motherduck_connection(db_name: str = None):
    """
    Establishes a connection to a MotherDuck database.
    
    Args:
        db_name (str, optional): Name of the database to connect to (e.g., 'ext_development').
                                 If None, connects to MotherDuck instance without a specific database.
    
    Returns:
        duckdb.DuckDBPyConnection: Active connection to the MotherDuck database
    
    Raises:
        ValueError: If MOTHERDUCK_TOKEN is not configured
        ConnectionError: If connection to MotherDuck fails
    
    Note:
        - When db_name is provided, database will be auto-created if it doesn't exist
        - When db_name is None, connects at instance level (useful for CREATE DATABASE)
        - Requires MOTHERDUCK_TOKEN to be set in environment variables
        - Connection should be closed after use with conn.close()
    """
    
    # Verify MotherDuck token is available
    token = DATABASE_CONFIG["motherduck_token"]
    if not token:
        raise ValueError("MOTHERDUCK_TOKEN not found. Please check your .env file.")
    
    try:
        # Connect to MotherDuck database using 'md:' prefix
        # Format: md:database_name automatically uses token from environment
        # If db_name is None, connect to MotherDuck instance without specific database
        connection_string = f"md:{db_name}" if db_name else "md:"
        conn = duckdb.connect(connection_string)
        
        # Verify connection is working with a simple test query
        conn.execute("SELECT 1").fetchone()
        
        return conn
        
    except Exception as e:
        db_context = f"'{db_name}'" if db_name else "instance"
        raise ConnectionError(f"Failed to connect to MotherDuck database {db_context}: {str(e)}")

def upsert_to_motherduck(df, database_name, schema, table_name, key_column):
    """
    Simple upsert DataFrame to MotherDuck table with _last_modified_timestamp.
    
    Args:
        df (pd.DataFrame): DataFrame to upsert
        database_name (str): MotherDuck database name (e.g., "ext_development")
        schema (str): Schema name
        table_name (str): Table name
        key_column (str): Column name to use as unique key for upsert
    """
    
    # Connect to MotherDuck database
    conn = get_motherduck_connection(database_name)
    
    try:
        # Create schema if it doesn't exist
        conn.execute(f"CREATE SCHEMA IF NOT EXISTS {database_name}.{schema}")
        
        # Add timestamp to DataFrame (Central Time, timezone-naive)
        df_with_timestamp = df.copy()
        central_time = pd.Timestamp.now(tz='America/Chicago')
        # Convert to naive timestamp (removes timezone info but keeps the time correct)
        df_with_timestamp['_last_modified_timestamp'] = central_time.tz_localize(None)
        
        # Register DataFrame with MotherDuck
        conn.register('df_temp', df_with_timestamp)
        
        # Full table path
        full_table_path = f"{database_name}.{schema}.{table_name}"
        
        # Check if table exists in MotherDuck
        table_exists = conn.execute(f"""
            SELECT COUNT(*) FROM information_schema.tables 
            WHERE table_catalog = '{database_name}'
              AND table_schema = '{schema}' 
              AND table_name = '{table_name}'
        """).fetchone()[0] > 0
        
        if not table_exists:
            # Create new table in MotherDuck
            conn.execute(f"""
                CREATE TABLE {full_table_path} AS 
                SELECT * FROM df_temp
            """)
            print(f"  ✓ Created new table: {full_table_path} with {len(df)} records")
        else:
            # Upsert: delete existing records with matching keys, then insert new data
            conn.execute(f"""
                DELETE FROM {full_table_path} 
                WHERE {key_column} IN (SELECT {key_column} FROM df_temp)
            """)
            conn.execute(f"""
                INSERT INTO {full_table_path} 
                SELECT * FROM df_temp
            """)
            print(f"  ✓ Upserted {len(df)} records to {full_table_path}")
        
    finally:
        conn.close()
        
def read_motherduck_table(database, schema, table_name):
    """
    Read a table from MotherDuck and return as DataFrame.
    
    Args:
        database (str): Database name (e.g., 'ext_dev')
        schema (str): Schema name (e.g., 'control', 'index')
        table_name (str): Table name (e.g., 'etl_process_control')
    
    Returns:
        pandas.DataFrame: Query results as DataFrame
    
    Example:
        df = read_motherduck_table('ext_dev', 'control', 'etl_process_control')
    """
    # Connect to MotherDuck database
    conn = get_motherduck_connection(database)
    
    try:
        # Build and execute query
        query = f"SELECT * FROM {schema}.{table_name}"
        df = conn.execute(query).df()
                
        return df
        
    finally:
        # Always close connection
        conn.close()

def format_duration(seconds):
    """
    Format duration in ##d ##h ##m ##s format.
    
    Args:
        seconds (float): Duration in seconds
        
    Returns:
        str: Formatted duration string
    """
    if seconds < 60:
        return f"{seconds:.0f}s"
    elif seconds < 3600:  # Less than 1 hour
        minutes = int(seconds // 60)
        remaining_seconds = int(seconds % 60)
        return f"{minutes}m {remaining_seconds}s"
    elif seconds < 86400:  # Less than 1 day (86400 seconds = 24 hours)
        hours = int(seconds // 3600)
        remaining_minutes = int((seconds % 3600) // 60)
        remaining_seconds = int(seconds % 60)
        return f"{hours}h {remaining_minutes}m {remaining_seconds}s"
    else:  # 1 day or more
        days = int(seconds // 86400)
        remaining_hours = int((seconds % 86400) // 3600)
        remaining_minutes = int((seconds % 3600) // 60)
        remaining_seconds = int(seconds % 60)
        return f"{days}d {remaining_hours}h {remaining_minutes}m {remaining_seconds}s"

def upsert_chunks_by_guid(df, database_name, schema, table_name, guid_column="guid"):
    """
    Upsert chunks by deleting all existing chunks for each GUID, then inserting new ones.
    This ensures old chunks are fully replaced even if chunk count changes.
    
    Args:
        df (pd.DataFrame): DataFrame to upsert (must include guid column)
        database_name (str): MotherDuck database name (e.g., 'ext_dev')
        schema (str): Schema name (e.g., 'silver')
        table_name (str): Table name (e.g., 'biblical_chunks')
        guid_column (str): Column containing document GUID (default: 'guid')
    """    
    conn = get_motherduck_connection(database_name)
    
    try:
        # Create schema if it doesn't exist
        conn.execute(f"CREATE SCHEMA IF NOT EXISTS {database_name}.{schema}")
        
        # Add timestamp to DataFrame (Central Time, timezone-naive)
        df_with_timestamp = df.copy()
        central_time = pd.Timestamp.now(tz='America/Chicago')
        df_with_timestamp['_last_modified_timestamp'] = central_time.tz_localize(None)
        
        # Register DataFrame with MotherDuck
        conn.register('df_temp', df_with_timestamp)
        
        # Full table path
        full_table_path = f"{database_name}.{schema}.{table_name}"
        
        # Check if table exists
        table_exists = conn.execute(f"""
            SELECT COUNT(*) FROM information_schema.tables 
            WHERE table_catalog = '{database_name}'
              AND table_schema = '{schema}' 
              AND table_name = '{table_name}'
        """).fetchone()[0] > 0
        
        if not table_exists:
            # Create new table
            conn.execute(f"""
                CREATE TABLE {full_table_path} AS 
                SELECT * FROM df_temp
            """)
            print(f"✓ Created new table: {full_table_path} with {len(df)} records")
        else:
            # Get unique GUIDs from the incoming data
            unique_guids = df[guid_column].unique()
            
            # Delete ALL existing chunks for these GUIDs
            for guid in unique_guids:
                conn.execute(f"""
                    DELETE FROM {full_table_path} 
                    WHERE {guid_column} = ?
                """, [guid])
            
            # Insert all new chunks
            conn.execute(f"""
                INSERT INTO {full_table_path} 
                SELECT * FROM df_temp
            """)
            
            print(f"✓ Replaced chunks for {len(unique_guids)} document(s) in {full_table_path}")
            print(f"✓ Total chunks inserted: {len(df)}")
        
    finally:
        conn.close()