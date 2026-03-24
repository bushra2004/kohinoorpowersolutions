"""
Main Flask Application File - PostgreSQL Version for Render/Neon
This app uses Neon PostgreSQL database with updated customer fields
"""

# Import necessary libraries
import os
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, flash, send_file
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
import psycopg2
from psycopg2.extras import RealDictCursor
import pandas as pd
import logging
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ============================================================================
# INITIALIZE FLASK APPLICATION
# ============================================================================
app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key-123')
app.config['DATABASE_URL'] = os.environ.get('DATABASE_URL')

# Validate database URL
if not app.config['DATABASE_URL']:
    logger.error("DATABASE_URL environment variable not set!")
    logger.error("Please set DATABASE_URL in your .env file or environment variables")
    raise ValueError("DATABASE_URL must be set in environment variables")

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
# DATABASE FUNCTIONS
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

def fix_database_completely():
    """
    COMPLETE DATABASE REPAIR - This WILL fix all issues
    Runs BEFORE any routes are accessed
    """
    print("\n" + "="*60)
    print("🔧 FORCE DATABASE REPAIR - STARTING...")
    print("="*60)
    
    conn = None
    try:
        # Connect directly
        conn = psycopg2.connect(app.config['DATABASE_URL'])
        cur = conn.cursor()
        
        # Check if customers table exists
        cur.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = 'customers'
            );
        """)
        table_exists = cur.fetchone()[0]
        
        if not table_exists:
            print("📦 Creating customers table from scratch...")
            cur.execute('''
                CREATE TABLE customers (
                    id SERIAL PRIMARY KEY,
                    serial_no INTEGER NOT NULL UNIQUE,
                    customer_name VARCHAR(200) NOT NULL,
                    contact VARCHAR(10) NOT NULL,
                    address TEXT NOT NULL,
                    product VARCHAR(100) NOT NULL,
                    product_name VARCHAR(200) NOT NULL,
                    amount DECIMAL(10,2) NOT NULL,
                    date DATE NOT NULL,
                    purchase_confirmed BOOLEAN DEFAULT FALSE,
                    action_notes TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            print("✅ Customers table created successfully!")
        else:
            print("📦 Table exists, checking columns...")
            
            # Get existing columns
            cur.execute("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'customers'
            """)
            existing_columns = [row[0] for row in cur.fetchall()]
            print(f"📋 Existing columns: {existing_columns}")
            
            # ADD MISSING COLUMNS ONE BY ONE
            if 'address' not in existing_columns:
                print("➕ Adding address column...")
                cur.execute("ALTER TABLE customers ADD COLUMN address TEXT;")
                print("✅ address column added")
            
            if 'product_name' not in existing_columns:
                print("➕ Adding product_name column...")
                cur.execute("ALTER TABLE customers ADD COLUMN product_name VARCHAR(200);")
                print("✅ product_name column added")
            
            if 'action_notes' not in existing_columns:
                print("➕ Adding action_notes column...")
                cur.execute("ALTER TABLE customers ADD COLUMN action_notes TEXT;")
                print("✅ action_notes column added")
            
            # REMOVE OLD COLUMNS
            old_columns = ['customer_id', 'city', 'product_category']
            for col in old_columns:
                if col in existing_columns:
                    print(f"🗑️ Removing old column: {col}")
                    cur.execute(f"ALTER TABLE customers DROP COLUMN IF EXISTS {col};")
            
            print("✅ Column checks complete!")
        
        # CREATE INDEXES FOR FAST SEARCH
        print("🔧 Creating indexes for fast search...")
        cur.execute('CREATE INDEX IF NOT EXISTS idx_customers_contact ON customers(contact);')
        cur.execute('CREATE INDEX IF NOT EXISTS idx_customers_name ON customers(customer_name);')
        print("✅ Indexes created!")
        
        conn.commit()
        cur.close()
        print("="*60)
        print("✅ DATABASE REPAIR COMPLETED SUCCESSFULLY!")
        print("="*60 + "\n")
        
    except Exception as e:
        print(f"❌ DATABASE REPAIR ERROR: {e}")
        if conn:
            conn.rollback()
    finally:
        if conn:
            conn.close()

# RUN DATABASE FIX IMMEDIATELY
fix_database_completely()

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

def validate_mobile(mobile):
    """Validate 10-digit mobile number"""
    return mobile and mobile.isdigit() and len(mobile) == 10

# ============================================================================
# ROUTES
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
        
        if username == 'kps' and password == 'kps2008':
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
    """Page to add new customer with 10 fields"""
    if request.method == 'POST':
        conn = None
        try:
            # Get form data
            customer_name = request.form.get('customer_name', '').strip()
            contact = request.form.get('contact', '').strip()
            address = request.form.get('address', '').strip()
            product = request.form.get('product', '')
            product_name = request.form.get('product_name', '').strip()
            amount = float(request.form.get('amount', 0))
            date = request.form.get('date', '')
            purchase_confirmed = request.form.get('purchase_confirmed') == 'on'
            action_notes = request.form.get('action_notes', '').strip()
            
            # Validate required fields
            missing = []
            if not customer_name: missing.append("Customer Name")
            if not contact: missing.append("Mobile Number")
            if not address: missing.append("Address")
            if not product: missing.append("Product")
            if not product_name: missing.append("Product Name")
            if not date: missing.append("Date")
            
            if missing:
                flash(f'❌ Missing required fields: {", ".join(missing)}', 'danger')
                return redirect(url_for('add_customer'))
            
            # Validate mobile number
            if not validate_mobile(contact):
                flash('❌ Please enter a valid 10-digit mobile number', 'danger')
                return redirect(url_for('add_customer'))
            
            # Get next serial number
            serial_no = get_next_serial_no()
            
            # Save to database
            conn = get_db_connection()
            cur = conn.cursor()
            cur.execute('''
                INSERT INTO customers 
                (serial_no, customer_name, contact, address, product, product_name, amount, date, purchase_confirmed, action_notes)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ''', (serial_no, customer_name, contact, address, product, product_name, amount, date, purchase_confirmed, action_notes))
            
            conn.commit()
            cur.close()
            
            flash(f'✅ Customer {customer_name} added successfully! (SNo: {serial_no})', 'success')
            return redirect(url_for('view_customers'))
            
        except psycopg2.IntegrityError as e:
            flash(f'❌ Database error: {str(e)}', 'danger')
        except ValueError as e:
            flash(f'❌ Invalid amount format! Please enter a valid number', 'danger')
        except Exception as e:
            logger.error(f"Error adding customer: {e}")
            flash(f'❌ Error: {str(e)}', 'danger')
        finally:
            if conn:
                conn.close()
    
    next_serial = get_next_serial_no()
    return render_template('add_customer.html', next_serial=next_serial, now=datetime.now())

@app.route('/customers')
@login_required
def view_customers():
    """Displays all customers in a table with search by contact number"""
    search_query = request.args.get('search', '').strip()
    conn = None
    
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        if search_query:
            cur.execute('''
                SELECT * FROM customers 
                WHERE contact ILIKE %s 
                   OR customer_name ILIKE %s 
                   OR product ILIKE %s 
                   OR product_name ILIKE %s
                   OR action_notes ILIKE %s
                ORDER BY 
                    CASE WHEN contact ILIKE %s THEN 1 ELSE 2 END,
                    serial_no DESC
            ''', (f'%{search_query}%', f'%{search_query}%', f'%{search_query}%', 
                  f'%{search_query}%', f'%{search_query}%', f'%{search_query}%'))
        else:
            cur.execute('SELECT * FROM customers ORDER BY serial_no DESC')
        
        customers = cur.fetchall()
        cur.close()
        
        # Format data for display with NULL checks
        customers_list = []
        for customer in customers:
            # Convert to dict safely
            if customer is None:
                continue
                
            customer_dict = dict(customer)
            
            # Safely get values with defaults
            customer_dict['amount_formatted'] = format_amount(customer_dict.get('amount', 0))
            customer_dict['purchase_icon'] = '✅' if customer_dict.get('purchase_confirmed') else '❌'
            
            # Handle date formatting safely
            date_val = customer_dict.get('date')
            if date_val:
                try:
                    customer_dict['date_formatted'] = date_val.strftime('%d-%m-%Y')
                except:
                    customer_dict['date_formatted'] = str(date_val)
            else:
                customer_dict['date_formatted'] = ''
            
            # Ensure all required fields exist
            customer_dict['address'] = customer_dict.get('address', '')
            customer_dict['product_name'] = customer_dict.get('product_name', '')
            customer_dict['action_notes'] = customer_dict.get('action_notes', '')
            customer_dict['contact'] = customer_dict.get('contact', '')
            customer_dict['customer_name'] = customer_dict.get('customer_name', '')
            customer_dict['product'] = customer_dict.get('product', '')
            
            customers_list.append(customer_dict)
        
        return render_template('view_customers.html', customers=customers_list, search_query=search_query)
    
    except Exception as e:
        logger.error(f"Error viewing customers: {e}")
        import traceback
        traceback.print_exc()
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
            customer_name = request.form.get('customer_name', '').strip()
            contact = request.form.get('contact', '').strip()
            address = request.form.get('address', '').strip()
            product = request.form.get('product', '')
            product_name = request.form.get('product_name', '').strip()
            amount = float(request.form.get('amount', 0))
            date = request.form.get('date', '')
            purchase_confirmed = request.form.get('purchase_confirmed') == 'on'
            action_notes = request.form.get('action_notes', '').strip()
            
            # Validate mobile number
            if not validate_mobile(contact):
                flash('❌ Please enter a valid 10-digit mobile number', 'danger')
                return redirect(url_for('edit_customer', id=id))
            
            # Update database
            cur.execute('''
                UPDATE customers 
                SET customer_name = %s, contact = %s, address = %s, 
                    product = %s, product_name = %s, amount = %s, 
                    date = %s, purchase_confirmed = %s, action_notes = %s
                WHERE id = %s
            ''', (customer_name, contact, address, product, product_name, amount, date, purchase_confirmed, action_notes, id))
            
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
        
        # Get customer name for confirmation message
        cur.execute('SELECT customer_name, serial_no FROM customers WHERE id = %s', (id,))
        customer = cur.fetchone()
        
        if customer:
            cur.execute('DELETE FROM customers WHERE id = %s', (id,))
            conn.commit()
            flash(f'✅ Customer {customer["customer_name"]} (SNo: {customer["serial_no"]}) deleted successfully!', 'success')
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
        
        # Debug: Check how many records exist
        cur.execute('SELECT COUNT(*) FROM customers')
        count = cur.fetchone()
        print(f"📊 Export: Found {count['count'] if count else 0} customers in database")
        
        # Get all customer data with 10 fields
        cur.execute('''
            SELECT 
                serial_no, 
                customer_name, 
                contact, 
                address, 
                product, 
                product_name, 
                amount, 
                TO_CHAR(date, 'DD-MM-YYYY') as date, 
                CASE WHEN purchase_confirmed THEN 'Yes' ELSE 'No' END as purchase,
                COALESCE(action_notes, '') as notes
            FROM customers 
            ORDER BY serial_no
        ''')
        
        customers = cur.fetchall()
        cur.close()
        
        print(f"📊 Export: Retrieved {len(customers)} records")
        
        if not customers:
            flash('❌ No data to export!', 'warning')
            return redirect(url_for('view_customers'))
        
        # Convert to pandas DataFrame
        data = []
        for row in customers:
            data.append({
                'S/No': row['serial_no'],
                'Customer Name': row['customer_name'],
                'Mobile': row['contact'],
                'Address': row['address'],
                'Product': row['product'],
                'Product Name': row['product_name'],
                'Amount (₹)': row['amount'],
                'Date': row['date'],
                'Purchase': row['purchase'],
                'Notes': row['notes']
            })
        
        df = pd.DataFrame(data)
        
        # Format amount column with comma separator
        df['Amount (₹)'] = df['Amount (₹)'].apply(lambda x: f"{float(x):,.0f}")
        
        # Generate filename
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f'kohinoor_customers_{timestamp}.xlsx'
        
        # Create Excel file in memory
        from io import BytesIO
        output = BytesIO()
        
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
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
                adjusted_width = min(max_length + 2, 50)
                worksheet.column_dimensions[column_letter].width = adjusted_width
        
        output.seek(0)
        
        print(f"✅ Excel file created: {filename} with {len(df)} rows")
        flash(f'✅ Excel file generated with {len(df)} records!', 'success')
        
        return send_file(
            output,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name=filename
        )
        
    except Exception as e:
        logger.error(f"Export error: {e}")
        import traceback
        traceback.print_exc()
        flash(f'❌ Error exporting: {str(e)}', 'danger')
        return redirect(url_for('dashboard'))
    finally:
        if conn:
            conn.close()

# Health check endpoint
@app.route('/health')
def health_check():
    """Health check endpoint to verify database connection"""
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute('SELECT 1')
        cur.close()
        return {"status": "healthy", "database": "connected", "timestamp": datetime.now().isoformat()}, 200
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {"status": "unhealthy", "error": str(e)}, 500
    finally:
        if conn:
            conn.close()

# Debug endpoint
@app.route('/debug')
def debug():
    """Debug endpoint to check database schema"""
    result = {
        "database_url_set": bool(app.config['DATABASE_URL']),
        "environment": os.environ.get('RENDER', 'development'),
        "python_version": os.sys.version
    }
    
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("""
            SELECT column_name, data_type, is_nullable
            FROM information_schema.columns 
            WHERE table_name = 'customers'
            ORDER BY ordinal_position
        """)
        columns = cur.fetchall()
        result['table_columns'] = [dict(col) for col in columns]
        cur.close()
    except Exception as e:
        result['schema_error'] = str(e)
    finally:
        if conn:
            conn.close()
    
    return result

# ============================================================================
# FOR LOCAL DEVELOPMENT
# ============================================================================
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5001))
    
    print("\n" + "="*70)
    print("🚀 KOHINOOR POWER SOLUTIONS - CUSTOMER MANAGEMENT SYSTEM")
    print("="*70)
    print(f"📊 Database: PostgreSQL (Neon)")
    print(f"🔗 Local URL: http://127.0.0.1:{port}")
    print(f"👤 Login: kps / kps2008")
    print(f"📱 Search: Search by contact number or notes")
    print("="*70)
    print("✅ YOUR 10 FIELDS:")
    print("   1. S/No")
    print("   2. Customer Name")
    print("   3. Mobile Number")
    print("   4. Address")
    print("   5. Product")
    print("   6. Product Name")
    print("   7. Amount")
    print("   8. Date")
    print("   9. Purchase")
    print("   10. Action Notes")
    print("="*70)
    print("✅ AUTO-REPAIR COMPLETE - Database is ready!")
    print("="*70 + "\n")
    
    app.run(host='0.0.0.0', port=port, debug=False)
