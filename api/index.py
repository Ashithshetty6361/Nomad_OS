import os
import sys

# Add project root to sys.path so 'app' and other modules resolve correctly
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from app.main import app

# Vercel looks for the ASGI/WSGI 'app' object
