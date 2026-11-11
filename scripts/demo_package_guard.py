#!/usr/bin/env python3
"""
Demo script for PackageGuard API integrations

Demonstrates real-world package evaluation with actual API calls.
"""

import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from home.package_guard import PackageGuard
import logging

# Enable logging to see API calls
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


def print_separator(char='=', length=80):
    """Print a visual separator."""
    print(char * length)


def evaluate_package(guard, package_name, version):
    """Evaluate a single package and display results."""
    print_separator()
    print(f"📦 Evaluating: {package_name}=={version}")
    print_separator()
    
    score = guard.evaluate(package_name, version)
    
    # Display results
    print(f"\n🎯 SCORE BREAKDOWN:")
    print(f"   Integrity:   {score.integrity:5.1f}/45  {'✓' if score.integrity >= 25 else '⚠'}")
    print(f"   Reputation:  {score.reputation:5.1f}/30  {'✓' if score.reputation >= 20 else '⚠'}")
    print(f"   Static:      {score.static_analysis:5.1f}/20  {'✓' if score.static_analysis >= 15 else '⚠'}")
    print(f"   Provenance:  {score.provenance:5.1f}/10  {'✓' if score.provenance >= 5 else '⚠'}")
    print(f"   " + "-" * 50)
    print(f"   TOTAL:       {score.total:5.1f}/105")
    print()
    
    # Decision
    if score.blocked:
        print(f"❌ BLOCKED: {score.reason}")
    elif score.is_safe(threshold=guard.min_score):
        print(f"✅ SAFE: Package meets safety threshold ({guard.min_score})")
    else:
        print(f"⛔ REJECTED: Package scored {score.total:.0f}, below threshold ({guard.min_score})")
    
    print()


def main():
    """Run demo evaluations."""
    print("\n" + "=" * 80)
    print("  PackageGuard API Integration Demo")
    print("  Real-time evaluation using PyPI, OSV.dev, and GitHub APIs")
    print("=" * 80)
    print()
    
    # Initialize guard with default threshold
    guard = PackageGuard(min_score=80)
    print(f"📊 Evaluation threshold: {guard.min_score}/105")
    print()
    
    # Test cases
    test_packages = [
        ("requests", "2.31.0", "Popular, mature package"),
        ("django", "4.2.0", "Large framework"),
        ("totally-unknown-pkg-xyz-123", "1.0.0", "Unknown package"),
        ("malicious-pkg", "1.0.0", "Known malicious (blocklist)"),
    ]
    
    for pkg_name, version, description in test_packages:
        print(f"📝 Test: {description}")
        try:
            evaluate_package(guard, pkg_name, version)
        except Exception as e:
            print(f"❌ Error evaluating {pkg_name}: {e}")
            print()
        
        print()
    
    print_separator()
    print("✨ Demo completed!")
    print()
    
    # Summary
    print("🔍 What was tested:")
    print("   ✓ PyPI JSON API - package metadata, hashes, publisher info")
    print("   ✓ OSV.dev API - real-time CVE lookups")
    print("   ✓ PyUp Safety DB - community vulnerability database")
    print("   ✓ pypistats.org - download statistics")
    print("   ✓ GitHub API - SLSA provenance checking")
    print("   ✓ Typosquatting detection - edit distance heuristics")
    print("   ✓ Blocklist mechanism - known malicious packages")
    print()


if __name__ == "__main__":
    main()
