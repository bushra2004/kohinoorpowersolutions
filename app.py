import os
import psycopg2
from psycopg2.extras import RealDictCursor
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_db_connection():
    """
    Get database connection using Vercel PostgreSQL environment variables
    """
    try:
        # Use Vercel's POSTGRES_URL environment variable
        database_url = os.environ.get('POSTGRES_URL')
        
        if not database_url:
            # Fallback to constructing from individual variables
            database_url = os.environ.get('DATABASE_URL')
            
            if not database_url:
                # Construct from individual PostgreSQL variables
                user = os.environ.get('POSTGRES_USER')
                password = os.environ.get('POSTGRES_PASSWORD')
                host = os.environ.get('POSTGRES_HOST')
                database = os.environ.get('POSTGRES_DATABASE')
                
                if all([user, password, host, database]):
                    database_url = f"postgresql://{user}:{password}@{host}/{database}?sslmode=require"
        
        if not database_url:
            raise ValueError("No database connection string found in environment variables")
        
        logger.info(f"Connecting to database at: {host if 'host' in locals() else 'using URL'}")
        
        # Connect with timeout
        conn = psycopg2.connect(
            database_url,
            connect_timeout=10,
            sslmode='require'
        )
        
        # Return dictionary-like rows
        conn.cursor_factory = RealDictCursor
        return conn
        
    except Exception as e:
        logger.error(f"Database connection failed: {e}")
        raise

def init_database():
    """
    Initialize database tables
    """
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Create customers table
        cur.execute('''
            CREATE TABLE IF NOT EXISTS customers (
                id SERIAL PRIMARY KEY,
                serial_no INTEGER NOT NULL,
                customer_id VARCHAR(50) UNIQUE NOT NULL,
                customer_name VARCHAR(200) NOT NULL,
                product VARCHAR(100) NOT NULL,
                date DATE NOT NULL,
                contact VARCHAR(50) NOT NULL,
                city VARCHAR(100) NOT NULL,
                amount DECIMAL(10,2) NOT NULL,
                purchase_confirmed BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Create index for faster searches
        cur.execute('''
            CREATE INDEX IF NOT EXISTS idx_customer_search 
            ON customers(customer_id, customer_name, product, city)
        ''')
        
        conn.commit()
        cur.close()
        logger.info("✅ Database initialized successfully!")
        
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        raise
    finally:
        if conn:
            conn.close()

@app.route('/api/health')
def health_check():
    """Health check endpoint to verify database connection"""
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute('SELECT 1')
        cur.close()
        
        # Check if tables exist
        cur = conn.cursor()
        cur.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = 'customers'
            );
        """)
        tables_exist = cur.fetchone()[0]
        cur.close()
        
        return {
            "status": "healthy",
            "database": "connected",
            "tables_exist": tables_exist,
            "environment": os.environ.get('VERCEL_ENV', 'development')
        }, 200
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {
            "status": "unhealthy",
            "error": str(e),
            "database_url_set": bool(os.environ.get('POSTGRES_URL'))
        }, 500
    finally:
        if conn:
            conn.close()