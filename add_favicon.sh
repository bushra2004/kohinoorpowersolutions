#!/bin/bash

# Add favicon to all HTML templates
for file in templates/*.html; do
    if [ -f "$file" ]; then
        echo "Updating $file..."
        
        # Create backup
        cp "$file" "$file.backup"
        
        # Add favicon link after title tag
        sed -i '' '/<title>/a\
    <link rel="icon" href="{{ url_for('\''static'\'', filename='\''logo.png'\'') }}" type="image/png">' "$file"
        
        echo "✅ Added favicon to $file"
    fi
done

# Update login page with logo display
if [ -f "templates/login.html" ]; then
    echo "Updating login page with logo..."
    cat > templates/login.html << 'LOGIN_EOF'
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Customer Management System</title>
    <link rel="icon" href="{{ url_for('static', filename='logo.png') }}" type="image/png">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; }
        body { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); height: 100vh; display: flex; justify-content: center; align-items: center; padding: 20px; }
        .login-container { width: 100%; max-width: 420px; animation: fadeIn 0.5s ease; }
        @keyframes fadeIn { from { opacity: 0; transform: translateY(20px); } to { opacity: 1; transform: translateY(0); } }
        .login-box { background: white; border-radius: 16px; padding: 40px; box-shadow: 0 20px 40px rgba(0,0,0,0.1); }
        .login-header { text-align: center; margin-bottom: 30px; }
        .logo-container { margin-bottom: 20px; }
        .logo { max-width: 120px; max-height: 120px; border-radius: 10px; box-shadow: 0 4px 8px rgba(0,0,0,0.1); }
        .login-header h1 { color: #2c3e50; margin-bottom: 10px; font-size: 28px; }
        .login-header p { color: #7f8c8d; font-size: 16px; }
        .alert { padding: 12px 16px; margin-bottom: 20px; border-radius: 8px; font-size: 14px; animation: slideIn 0.3s ease; }
        @keyframes slideIn { from { transform: translateX(-20px); opacity: 0; } to { transform: translateX(0); opacity: 1; } }
        .alert-success { background-color: #d4edda; border: 1px solid #c3e6cb; color: #155724; }
        .alert-danger { background-color: #f8d7da; border: 1px solid #f5c6cb; color: #721c24; }
        .form-group { margin-bottom: 20px; }
        label { display: block; margin-bottom: 8px; color: #2c3e50; font-weight: 600; font-size: 14px; }
        input { width: 100%; padding: 14px 16px; border: 2px solid #e0e0e0; border-radius: 10px; font-size: 16px; transition: all 0.3s ease; background-color: #f8f9fa; }
        input:focus { outline: none; border-color: #3498db; background-color: white; box-shadow: 0 0 0 3px rgba(52,152,219,0.1); }
        .btn-login { width: 100%; padding: 15px; background: linear-gradient(135deg, #3498db, #1a73e8); color: white; border: none; border-radius: 10px; font-size: 16px; font-weight: 600; cursor: pointer; transition: all 0.3s ease; margin-top: 10px; }
        .btn-login:hover { transform: translateY(-2px); box-shadow: 0 10px 20px rgba(52,152,219,0.3); }
        .login-info { margin-top: 20px; padding: 15px; background-color: #f8f9fa; border-radius: 8px; border-left: 4px solid #2980b9; font-size: 14px; }
        .login-info p { margin: 5px 0; color: #555; }
        .login-info code { background-color: #e8f4fc; padding: 2px 6px; border-radius: 4px; font-family: monospace; color: #2980b9; }
        .login-footer { text-align: center; margin-top: 20px; color: rgba(255,255,255,0.8); font-size: 14px; }
    </style>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
</head>
<body>
    <div class="login-container">
        <div class="login-box">
            <div class="login-header">
                <div class="logo-container">
                    <img src="{{ url_for('static', filename='logo.png') }}" alt="Company Logo" class="logo">
                </div>
                <h1>Customer Management</h1>
                <p>Administrator Login</p>
            </div>
            {% with messages = get_flashed_messages(with_categories=true) %}
                {% if messages %}
                    {% for category, message in messages %}
                        <div class="alert alert-{{ category }}">{{ message }}</div>
                    {% endfor %}
                {% endif %}
            {% endwith %}
            <form method="POST" action="{{ url_for('login') }}" class="login-form">
                <div class="form-group">
                    <label for="username"><i class="fas fa-user"></i> Username</label>
                    <input type="text" id="username" name="username" placeholder="Enter admin username" required value="admin">
                </div>
                <div class="form-group">
                    <label for="password"><i class="fas fa-lock"></i> Password</label>
                    <input type="password" id="password" name="password" placeholder="Enter password" required value="admin123">
                </div>
                <button type="submit" class="btn-login"><i class="fas fa-sign-in-alt"></i> Login</button>
                <div class="login-info">
                    <p><strong>Default Credentials:</strong></p>
                    <p>Username: <code>admin</code></p>
                    <p>Password: <code>admin123</code></p>
                </div>
            </form>
        </div>
        <div class="login-footer">
            <p>© 2024 Customer Management System | All Rights Reserved</p>
        </div>
    </div>
</body>
</html>
LOGIN_EOF
    echo "✅ Updated login page"
fi

echo "🎉 Logo integration complete!"
echo "Make sure your logo.png is in the static/ folder"
