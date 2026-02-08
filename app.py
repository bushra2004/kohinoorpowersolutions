"""
Main Flask Application File
This is the heart of our web application
"""

# Import necessary libraries
import os
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, flash, send_file, session
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
import sqlite3
import pandas as pd
from werkzeug.security import generate_password_hash, check_password_hash

# ============================================================================
# INITIALIZE FLASK APPLICATION
# ============================================================================
app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-123'  # Required for session security
app.config['DATABASE'] = 'instance/customers.db'  # Path to SQLite database

# ============================================================================
# SETUP LOGIN MANAGER
# ============================================================================
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'  # Redirect unauthorized users to login page

# ============================================================================
# USER CLASS FOR AUTHENTICATION
# ============================================================================
class User(UserMixin):
    """
    Represents a user in our system
    Currently only one admin user is supported
    """
    def __init__(self, id):
        self.id = id
        self.username = "admin"

# Create our single admin user
admin_user = User(1)

@login_manager.user_loader
def load_user(user_id):
    """
    This function is called by Flask-Login to load a user from the user_id
    """
    if user_id == '1':
        return admin_user
    return None

# ============================================================================
# DATABASE FUNCTIONS
# ============================================================================
def get_db_connection():
    """
    Establishes connection to SQLite database
    Returns a connection object and cursor for database operations
    """
    conn = sqlite3.connect(app.config['DATABASE'])
    conn.row_factory = sqlite3.Row  # Return rows as dictionaries
    return conn

def init_database():
    """
    Creates the database and tables if they don't exist
    This runs automatically when the app starts
    """
    # Create instance directory if it doesn't exist
    if not os.path.exists('instance'):
        os.makedirs('instance')
    
    # Create exports directory for Excel files
    if not os.path.exists('exports'):
        os.makedirs('exports')
    
    conn = get_db_connection()
    
    # Create customers table with all required fields
    conn.execute('''
        CREATE TABLE IF NOT EXISTS customers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            serial_no INTEGER NOT NULL,
            customer_id TEXT UNIQUE NOT NULL,
            customer_name TEXT NOT NULL,
            product TEXT NOT NULL,
            date DATE NOT NULL,
            contact TEXT NOT NULL,
            city TEXT NOT NULL,
            amount REAL NOT NULL,
            purchase_confirmed BOOLEAN DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    conn.commit()
    conn.close()
    print("Database initialized successfully!")

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================
def get_next_serial_no():
    """
    Gets the next serial number by finding the maximum in the database
    """
    conn = get_db_connection()
    result = conn.execute('SELECT MAX(serial_no) FROM customers').fetchone()
    conn.close()
    
    if result[0] is None:
        return 1  # First record
    return result[0] + 1

def format_amount(amount):
    """
    Formats amount with comma separator (Indian style: 50,000)
    """
    return f"{amount:,.0f}"

# ============================================================================
# ROUTES (WEB PAGES)
# ============================================================================
@app.route('/')
def home():
    """
    Home page - redirects to login if not authenticated, otherwise to dashboard
    """
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    """
    Login page - handles user authentication
    GET: Shows login form
    POST: Processes login credentials
    """
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        # Hardcoded admin credentials (in real app, store in database)
        if username == 'admin' and password == 'admin123':
            login_user(admin_user)
            flash('Login successful!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('❌ Invalid username or password', 'danger')
    
    return render_template('login.html')

@app.route('/logout')
@login_required  # Only logged-in users can logout
def logout():
    """
    Logs out the current user
    """
    logout_user()
    flash('Logged out successfully', 'info')
    return redirect(url_for('login'))

@app.route('/dashboard')
@login_required
def dashboard():
    """
    Main dashboard after login
    Shows welcome message and navigation options
    """
    conn = get_db_connection()
    total_customers = conn.execute('SELECT COUNT(*) FROM customers').fetchone()[0]
    total_amount = conn.execute('SELECT SUM(amount) FROM customers').fetchone()[0] or 0
    conn.close()
    
    return render_template('dashboard.html', 
                         total_customers=total_customers,
                         total_amount=format_amount(total_amount))

@app.route('/add', methods=['GET', 'POST'])
@login_required
def add_customer():
    """
    Page to add new customer
    GET: Shows empty form
    POST: Saves new customer to database
    """
    if request.method == 'POST':
        try:
            # Get form data
            customer_id = request.form.get('customer_id')
            customer_name = request.form.get('customer_name')
            product = request.form.get('product')
            date = request.form.get('date')
            contact = request.form.get('contact')
            city = request.form.get('city')
            amount = float(request.form.get('amount'))
            
            # Checkbox returns 'on' if checked, None if not
            purchase_confirmed = 1 if request.form.get('purchase_confirmed') else 0
            
            # Get next serial number
            serial_no = get_next_serial_no()
            
            # Save to database
            conn = get_db_connection()
            conn.execute('''
                INSERT INTO customers 
                (serial_no, customer_id, customer_name, product, date, contact, city, amount, purchase_confirmed)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (serial_no, customer_id, customer_name, product, date, contact, city, amount, purchase_confirmed))
            
            conn.commit()
            conn.close()
            
            flash(f'✅ Customer {customer_id} added successfully!', 'success')
            return redirect(url_for('view_customers'))
            
        except sqlite3.IntegrityError:
            flash(f'❌ Customer ID {customer_id} already exists!', 'danger')
        except Exception as e:
            flash(f'❌ Error: {str(e)}', 'danger')
    
    # For GET request, show form with next serial number
    next_serial = get_next_serial_no()
    return render_template('add_customer.html', next_serial=next_serial)

@app.route('/customers')
@login_required
def view_customers():
    search_query = request.args.get('search', '')
    
    conn = get_db_connection()
    
    if search_query:
        customers = conn.execute('''
            SELECT * FROM customers 
            WHERE customer_id LIKE ? OR customer_name LIKE ? OR product LIKE ? OR city LIKE ?
            ORDER BY serial_no
        ''', (f'%{search_query}%', f'%{search_query}%', f'%{search_query}%', f'%{search_query}%')).fetchall()
    else:
        customers = conn.execute('SELECT * FROM customers ORDER BY serial_no').fetchall()
    
    conn.close()
    
    # FIX: Convert to list of dictionaries
    customers_list = []
    for customer in customers:
        customer_dict = dict(customer)
        customer_dict['amount_formatted'] = format_amount(customer_dict['amount'])
        customer_dict['purchase_icon'] = '✅' if customer_dict['purchase_confirmed'] else '❌'
        customers_list.append(customer_dict)
    
    return render_template('view_customers.html', customers=customers_list, search_query=search_query)

@app.route('/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_customer(id):
    """
    Edit an existing customer
    GET: Shows form with existing data
    POST: Updates the customer in database
    """
    conn = get_db_connection()
    
    if request.method == 'POST':
        try:
            # Get updated form data
            customer_id = request.form.get('customer_id')
            customer_name = request.form.get('customer_name')
            product = request.form.get('product')
            date = request.form.get('date')
            contact = request.form.get('contact')
            city = request.form.get('city')
            amount = float(request.form.get('amount'))
            purchase_confirmed = 1 if request.form.get('purchase_confirmed') else 0
            
            # Update database
            conn.execute('''
                UPDATE customers 
                SET customer_id = ?, customer_name = ?, product = ?, date = ?, 
                    contact = ?, city = ?, amount = ?, purchase_confirmed = ?
                WHERE id = ?
            ''', (customer_id, customer_name, product, date, contact, city, amount, purchase_confirmed, id))
            
            conn.commit()
            flash('✅ Customer updated successfully!', 'success')
            return redirect(url_for('view_customers'))
            
        except Exception as e:
            flash(f'❌ Error: {str(e)}', 'danger')
    
    # GET request - load existing customer data
    customer = conn.execute('SELECT * FROM customers WHERE id = ?', (id,)).fetchone()
    conn.close()
    
    if customer is None:
        flash('❌ Customer not found!', 'danger')
        return redirect(url_for('view_customers'))
    
    return render_template('edit_customer.html', customer=customer)

@app.route('/delete/<int:id>')
@login_required
def delete_customer(id):
    """
    Deletes a customer from the database
    """
    conn = get_db_connection()
    
    # Get customer ID for confirmation message
    customer = conn.execute('SELECT customer_id FROM customers WHERE id = ?', (id,)).fetchone()
    
    if customer:
        conn.execute('DELETE FROM customers WHERE id = ?', (id,))
        conn.commit()
        flash(f'✅ Customer {customer["customer_id"]} deleted successfully!', 'success')
    else:
        flash('❌ Customer not found!', 'danger')
    
    conn.close()
    return redirect(url_for('view_customers'))

@app.route('/export')
@login_required
def export_to_excel():
    """
    Exports all customer data to an Excel file and downloads it
    """
    try:
        conn = get_db_connection()
        
        # Get all customer data
        customers = conn.execute('''
            SELECT serial_no, customer_id, customer_name, product, date, 
                   contact, city, amount, 
                   CASE WHEN purchase_confirmed = 1 THEN 'Yes' ELSE 'No' END as purchase_confirmed
            FROM customers 
            ORDER BY serial_no
        ''').fetchall()
        
        conn.close()
        
        # Convert to pandas DataFrame
        df = pd.DataFrame(customers, columns=[
            'Serial No', 'Customer ID', 'Customer Name', 'Product', 'Date',
            'Contact', 'City', 'Amount', 'Purchase Confirmed'
        ])
        
        # Format amount column with comma separator
        df['Amount'] = df['Amount'].apply(lambda x: f"{x:,.0f}")
        
        # Generate filename with timestamp
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f'customers_{timestamp}.xlsx'
        filepath = f'exports/{filename}'
        
        # Create Excel file using pandas
        with pd.ExcelWriter(filepath, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='Customers', index=False)
            
            # Get the worksheet for formatting
            worksheet = writer.sheets['Customers']
            
            # Auto-adjust column widths
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
        
        flash(f'✅ Excel file generated successfully: {filename}', 'success')
        
        # Send file for download
        return send_file(filepath, as_attachment=True, download_name=filename)
        
    except Exception as e:
        flash(f'❌ Error exporting to Excel: {str(e)}', 'danger')
        return redirect(url_for('dashboard'))

# ============================================================================
# RUN THE APPLICATION
# ============================================================================
if __name__ == '__main__':
    # Initialize database on startup
    init_database()
    
    # Run the Flask app
    print("🚀 Starting Customer Management App...")
    print("📊 Database: instance/customers.db")
    print("🔗 Local URL: http://127.0.0.1:5001")
    print("👤 Login with: admin / admin123")
    
    app.run(host='0.0.0.0', port=5001, debug=True)