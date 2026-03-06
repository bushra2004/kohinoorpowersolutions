import sys
import os

# Add your project directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

from app import app

def handler(event, context):
    """Handle the incoming request"""
    from flask_lambda import FlaskLambda
    return FlaskLambda(app)(event, context)