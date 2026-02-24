#!/usr/bin/env python3
"""
Test script to verify all dependencies can be imported.
This uses the same robust version checking as the GitHub Actions workflow.
"""

import sys


def get_version(module_name):
    """Get version of a module, handling missing __version__ attribute."""
    try:
        mod = __import__(module_name)
        # Try __version__ first
        if hasattr(mod, '__version__'):
            return mod.__version__
        # Fall back to importlib.metadata
        try:
            from importlib.metadata import version
            return version(module_name)
        except Exception:
            # If all else fails, just confirm it imports
            return "installed"
    except ImportError as e:
        print(f"❌ {module_name}: NOT FOUND - {e}")
        return None


def main():
    """Test all critical dependencies."""
    print("=" * 60)
    print("Testing Critical Dependencies")
    print("=" * 60)
    print()
    
    # Check each dependency
    packages = [
        ('fastmcp', 'fastmcp'),
        ('uvicorn', 'uvicorn'),
        ('starlette', 'starlette'),
        ('httpx', 'httpx'),
        ('aiofiles', 'aiofiles'),
    ]
    
    all_ok = True
    for display_name, module_name in packages:
        ver = get_version(module_name)
        if ver:
            print(f"✅ {display_name}: {ver}")
        else:
            all_ok = False
    
    # Special case for python-dotenv
    try:
        from dotenv import load_dotenv
        print("✅ python-dotenv: OK")
    except ImportError as e:
        print(f"❌ python-dotenv: NOT FOUND - {e}")
        all_ok = False
    
    print()
    if all_ok:
        print("✅ All critical dependencies verified!")
        print()
        print("=" * 60)
        print("You can now run the server:")
        print("  python server.py")
        print("=" * 60)
        return 0
    else:
        print("❌ Some dependencies are missing!")
        print()
        print("=" * 60)
        print("Install missing dependencies:")
        print("  pip install -r requirements.txt")
        print("=" * 60)
        return 1


if __name__ == "__main__":
    sys.exit(main())
