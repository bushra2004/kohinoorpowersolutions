"""
Main Flask Application File - PostgreSQL Version for Vercel
This app uses Neon PostgreSQL database (cloud) instead of SQLite
"""

# Import necessary libraries
import os
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, flash, send_file, session
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
import psycopg2
from psycopg2.extras import RealDictCursor
from psycopg2 import sql
import pandas as pd
from werkzeug.security import generate_password_hash, check_password_hash
from urllib.parse import urlparse
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ============================================================================
# INITIALIZE FLASK APPLICATION
# ============================================================================
app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key-123')  # Get from environment
app.config['DATABASE_URL'] = os.environ.get('DATABASE_URL')  # PostgreSQL connection string

# Validate database URL
if not app.config['DATABASE_URL']:
    logger.error("DATABASE_URL environment variable not set!")
    raise ValueError("DATABASE_URL must be set")

# ============================================================================
# SETUP LOGIN MANAGER
# ============================================================================
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = "Please log in to access this page."

# ============================================================================
# USER CLASS FOR AUTHENTICATION
# ============================================================================
class User(UserMixin):
    """Admin user class"""
    def __init__(self, id):
        self.id = id
        self.username = "admin"

admin_user = User(1)

@login_manager.user_loader
def load_user(user_id):
    """Load user from session"""
    if user_id == '1':
        return admin_user
    return None

# ============================================================================
# DATABASE FUNCTIONS - PostgreSQL Version
# ============================================================================
def get_db_connection():
    """
    Establishes connection to PostgreSQL database (Neon)
    Returns a connection object with RealDictCursor for dictionary-like access
    """
    try:
        conn = psycopg2.connect(app.config['DATABASE_URL'], cursor_factory=RealDictCursor)
        return conn
    except Exception as e:
        logger.error(f"Database connection failed: {e}")
        raise

def init_database():
    """
    Creates the customers table if it doesn't exist
    Also creates exports directory for Excel files
    """
    # Create exports directory for Excel files (local only)
    if not os.path.exists('exports'):
        os.makedirs('exports')
        logger.info("Created exports directory")
    
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Create customers table with PostgreSQL syntax
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
        logger.info("✅ PostgreSQL database initialized successfully!")
        
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        raise
    finally:
        if conn:
            conn.close()

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================
def get_next_serial_no():
    """Gets the next serial number by finding the maximum in the database"""
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute('SELECT MAX(serial_no) FROM customers')
        result = cur.fetchone()
        cur.close()
        
        if result['max'] is None:
            return 1
        return result['max'] + 1
    except Exception as e:
        logger.error(f"Error getting next serial number: {e}")
        return 1
    finally:
        if conn:
            conn.close()

def format_amount(amount):
    """Formats amount with comma separator (Indian style: 50,000)"""
    try:
        return f"{float(amount):,.0f}"
    except:
        return "0"

# ============================================================================
# ROUTES (WEB PAGES)
# ============================================================================
@app.route('/')
def home():
    """Home page - redirects to login or dashboard"""
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Login page - handles user authentication"""
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        if username == 'admin' and password == 'admin123':
            login_user(admin_user)
            flash('✅ Login successful!', 'success')
            next_page = request.args.get('next')
            return redirect(next_page) if next_page else redirect(url_for('dashboard'))
        else:
            flash('❌ Invalid username or password', 'danger')
    
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    """Logs out the current user"""
    logout_user()
    flash('👋 Logged out successfully', 'info')
    return redirect(url_for('login'))

@app.route('/dashboard')
@login_required
def dashboard():
    """Main dashboard after login"""
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        cur.execute('SELECT COUNT(*) FROM customers')
        total_customers = cur.fetchone()['count']
        
        cur.execute('SELECT COALESCE(SUM(amount), 0) FROM customers')
        total_amount = cur.fetchone()['coalesce']
        
        cur.close()
        
        return render_template('dashboard.html', 
                             total_customers=total_customers,
                             total_amount=format_amount(total_amount))
    except Exception as e:
        logger.error(f"Dashboard error: {e}")
        flash('Error loading dashboard', 'danger')
        return render_template('dashboard.html', total_customers=0, total_amount="0")
    finally:
        if conn:
            conn.close()

@app.route('/add', methods=['GET', 'POST'])
@login_required
def add_customer():
    """Page to add new customer"""
    if request.method == 'POST':
        conn = None
        try:
            # Get form data
            customer_id = request.form.get('customer_id')
            customer_name = request.form.get('customer_name')
            product = request.form.get('product')
            date = request.form.get('date')
            contact = request.form.get('contact')
            city = request.form.get('city')
            amount = float(request.form.get('amount', 0))
            purchase_confirmed = request.form.get('purchase_confirmed') == 'on'
            
            # Validate required fields
            if not all([customer_id, customer_name, product, date, contact, city]):
                flash('❌ All fields are required!', 'danger')
                return redirect(url_for('add_customer'))
            
            # Get next serial number
            serial_no = get_next_serial_no()
            
            # Save to database
            conn = get_db_connection()
            cur = conn.cursor()
            cur.execute('''
                INSERT INTO customers 
                (serial_no, customer_id, customer_name, product, date, contact, city, amount, purchase_confirmed)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            ''', (serial_no, customer_id, customer_name, product, date, contact, city, amount, purchase_confirmed))
            
            conn.commit()
            cur.close()
            
            flash(f'✅ Customer {customer_id} added successfully!', 'success')
            return redirect(url_for('view_customers'))
            
        except psycopg2.IntegrityError:
            flash(f'❌ Customer ID {customer_id} already exists!', 'danger')
        except ValueError as e:
            flash(f'❌ Invalid amount format!', 'danger')
        except Exception as e:
            logger.error(f"Error adding customer: {e}")
            flash(f'❌ Error: {str(e)}', 'danger')
        finally:
            if conn:
                conn.close()
    
    # For GET request, show form with next serial number
    next_serial = get_next_serial_no()
    return render_template('add_customer.html', next_serial=next_serial)

@app.route('/customers')
@login_required
def view_customers():
    """Displays all customers in a table with search functionality"""
    search_query = request.args.get('search', '')
    conn = None
    
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        if search_query:
            # Search across multiple columns using PostgreSQL ILIKE (case-insensitive)
            cur.execute('''
                SELECT * FROM customers 
                WHERE customer_id ILIKE %s 
                   OR customer_name ILIKE %s 
                   OR product ILIKE %s 
                   OR city ILIKE %s
                ORDER BY serial_no
            ''', (f'%{search_query}%', f'%{search_query}%', f'%{search_query}%', f'%{search_query}%'))
        else:
            cur.execute('SELECT * FROM customers ORDER BY serial_no')
        
        customers = cur.fetchall()
        cur.close()
        
        # Convert to list of dictionaries and add formatted fields
        customers_list = []
        for customer in customers:
            customer_dict = dict(customer)
            customer_dict['amount_formatted'] = format_amount(customer_dict['amount'])
            customer_dict['purchase_icon'] = '✅' if customer_dict['purchase_confirmed'] else '❌'
            customers_list.append(customer_dict)
        
        return render_template('view_customers.html', customers=customers_list, search_query=search_query)
    
    except Exception as e:
        logger.error(f"Error viewing customers: {e}")
        flash('Error loading customers', 'danger')
        return render_template('view_customers.html', customers=[], search_query=search_query)
    finally:
        if conn:
            conn.close()

@app.route('/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_customer(id):
    """Edit an existing customer"""
    conn = None
    
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        if request.method == 'POST':
            # Get updated form data
            customer_id = request.form.get('customer_id')
            customer_name = request.form.get('customer_name')
            product = request.form.get('product')
            date = request.form.get('date')
            contact = request.form.get('contact')
            city = request.form.get('city')
            amount = float(request.form.get('amount', 0))
            purchase_confirmed = request.form.get('purchase_confirmed') == 'on'
            
            # Update database
            cur.execute('''
                UPDATE customers 
                SET customer_id = %s, customer_name = %s, product = %s, date = %s, 
                    contact = %s, city = %s, amount = %s, purchase_confirmed = %s
                WHERE id = %s
            ''', (customer_id, customer_name, product, date, contact, city, amount, purchase_confirmed, id))
            
            conn.commit()
            flash('✅ Customer updated successfully!', 'success')
            return redirect(url_for('view_customers'))
        
        # GET request - load existing customer data
        cur.execute('SELECT * FROM customers WHERE id = %s', (id,))
        customer = cur.fetchone()
        
        if customer is None:
            flash('❌ Customer not found!', 'danger')
            return redirect(url_for('view_customers'))
        
        return render_template('edit_customer.html', customer=dict(customer))
    
    except Exception as e:
        logger.error(f"Error editing customer: {e}")
        flash(f'❌ Error: {str(e)}', 'danger')
        return redirect(url_for('view_customers'))
    finally:
        if conn:
            conn.close()

@app.route('/delete/<int:id>')
@login_required
def delete_customer(id):
    """Deletes a customer from the database"""
    conn = None
    
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Get customer ID for confirmation message
        cur.execute('SELECT customer_id FROM customers WHERE id = %s', (id,))
        customer = cur.fetchone()
        
        if customer:
            cur.execute('DELETE FROM customers WHERE id = %s', (id,))
            conn.commit()
            flash(f'✅ Customer {customer["customer_id"]} deleted successfully!', 'success')
        else:
            flash('❌ Customer not found!', 'danger')
        
        return redirect(url_for('view_customers'))
    
    except Exception as e:
        logger.error(f"Error deleting customer: {e}")
        flash(f'❌ Error: {str(e)}', 'danger')
        return redirect(url_for('view_customers'))
    finally:
        if conn:
            conn.close()

@app.route('/export')
@login_required
def export_to_excel():
    """Exports all customer data to an Excel file and downloads it"""
    conn = None
    
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Get all customer data
        cur.execute('''
            SELECT serial_no, customer_id, customer_name, product, 
                   TO_CHAR(date, 'YYYY-MM-DD') as date, 
                   contact, city, amount, 
                   CASE WHEN purchase_confirmed THEN 'Yes' ELSE 'No' END as purchase_confirmed
            FROM customers 
            ORDER BY serial_no
        ''')
        
        customers = cur.fetchall()
        cur.close()
        
        if not customers:
            flash('❌ No data to export!', 'warning')
            return redirect(url_for('view_customers'))
        
        # Convert to pandas DataFrame
        df = pd.DataFrame(customers, columns=[
            'Serial No', 'Customer ID', 'Customer Name', 'Product', 'Date',
            'Contact', 'City', 'Amount', 'Purchase Confirmed'
        ])
        
        # Format amount column with comma separator
        df['Amount'] = df['Amount'].apply(lambda x: f"{float(x):,.0f}")
        
        # Generate filename with timestamp
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f'customers_{timestamp}.xlsx'
        filepath = f'exports/{filename}'
        
        # Create Excel file
        with pd.ExcelWriter(filepath, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='Customers', index=False)
            
            # Auto-adjust column widths
            worksheet = writer.sheets['Customers']
            for column in worksheet.columns:
                max_length = 0
                column_letter = column[0].column_letter
                for cell in column:
                    try:
                        if len(str(cell.value)) > max_length:
                            max_length = len(str(cell.value))
                    except:
                        pass
                adjusted_width = min(max_length + 2, 30)
                worksheet.column_dimensions[column_letter].width = adjusted_width
        
        flash(f'✅ Excel file generated: {filename}', 'success')
        return send_file(filepath, as_attachment=True, download_name=filename)
        
    except Exception as e:
        logger.error(f"Export error: {e}")
        flash(f'❌ Error exporting: {str(e)}', 'danger')
        return redirect(url_for('dashboard'))
    finally:
        if conn:
            conn.close()

# Health check endpoint for Vercel
@app.route('/api/health')
def health_check():
    """Health check endpoint to verify database connection"""
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute('SELECT 1')
        cur.close()
        return {"status": "healthy", "database": "connected"}, 200
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {"status": "unhealthy", "error": str(e)}, 500
    finally:
        if conn:
            conn.close()

# ============================================================================
# FOR LOCAL DEVELOPMENT
# ============================================================================
if __name__ == '__main__':
    # Initialize database
    init_database()
    
    print("=" * 60)
    print("🚀 KOHINOOR POWER SOLUTIONS - CUSTOMER MANAGEMENT")
    print("=" * 60)
    print("📊 Database: PostgreSQL (Neon)")
    print("🔗 Local URL: http://127.0.0.1:5001")
    print("👤 Login: admin / admin123")
    print("=" * 60)
    
    app.run(host='0.0.0.0', port=5001, debug=True)
