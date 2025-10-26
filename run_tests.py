#!/usr/bin/env python
"""
Test runner script for Zpredict API tests
Run this script to execute all tests or specific test classes
"""

import os
import sys
import django
from django.conf import settings
from django.test.utils import get_runner

def run_tests():
    """Run the test suite"""
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'zpredict.settings')
    django.setup()
    
    TestRunner = get_runner(settings)
    test_runner = TestRunner()
    
    # Run all tests
    failures = test_runner.run_tests(['api.tests'])
    
    if failures:
        sys.exit(1)
    else:
        print("\n✅ All tests passed successfully!")
        sys.exit(0)

def run_specific_test(test_class):
    """Run a specific test class"""
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'zpredict.settings')
    django.setup()
    
    TestRunner = get_runner(settings)
    test_runner = TestRunner()
    
    # Run specific test class
    failures = test_runner.run_tests([f'api.tests.{test_class}'])
    
    if failures:
        sys.exit(1)
    else:
        print(f"\n✅ All tests in {test_class} passed successfully!")
        sys.exit(0)

if __name__ == '__main__':
    if len(sys.argv) > 1:
        # Run specific test class
        test_class = sys.argv[1]
        run_specific_test(test_class)
    else:
        # Run all tests
        run_tests()
