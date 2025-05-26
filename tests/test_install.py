#!/usr/bin/env python3
"""
Test script to verify Launchonomy package installation.
Run this after installing the package to ensure everything works.
"""

import sys
import importlib.util

def test_import(module_name):
    """Test if a module can be imported."""
    try:
        spec = importlib.util.find_spec(module_name)
        if spec is None:
            return False, f"Module {module_name} not found"
        
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return True, f"✅ {module_name} imported successfully"
    except Exception as e:
        return False, f"❌ {module_name} import failed: {str(e)}"

def test_cli_entry_point():
    """Test if the CLI entry point is available."""
    try:
        import subprocess
        result = subprocess.run([sys.executable, "-c", "import launchonomy.cli; print('CLI module available')"], 
                              capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            return True, "✅ CLI entry point available"
        else:
            return False, f"❌ CLI entry point failed: {result.stderr}"
    except Exception as e:
        return False, f"❌ CLI entry point test failed: {str(e)}"

def main():
    """Run installation tests."""
    print("🚀 Testing Launchonomy Installation")
    print("=" * 50)
    
    tests = [
        ("Core package", lambda: test_import("launchonomy")),
        ("CLI module", lambda: test_import("launchonomy.cli")),
        ("Core orchestrator", lambda: test_import("launchonomy.core.orchestrator")),
        ("Registry system", lambda: test_import("launchonomy.registry.registry")),
        ("CLI entry point", test_cli_entry_point),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\nTesting {test_name}...")
        try:
            success, message = test_func()
            print(f"  {message}")
            if success:
                passed += 1
        except Exception as e:
            print(f"  ❌ {test_name} test crashed: {str(e)}")
    
    print("\n" + "=" * 50)
    print(f"Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! Launchonomy is ready to use.")
        print("\nTo get started, run:")
        print("  launchonomy --help")
        return 0
    else:
        print("⚠️  Some tests failed. Check the error messages above.")
        print("\nCommon issues:")
        print("- Missing dependencies: pip install chromadb autogen-core")
        print("- Environment setup: export OPENAI_API_KEY=your-key")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 