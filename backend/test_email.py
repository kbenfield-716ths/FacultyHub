"""
Test script for PCCM Faculty Hub email notifications using Resend
Run this to verify your Resend setup is working
"""

import os
import sys
from datetime import datetime, timedelta

# Add parent directory to path to import email_service
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from email_service import (
    send_irpa_confirmation,
    send_unavailability_confirmation,
    RESEND_API_KEY
)


def test_email_setup():
    """Verify Resend API key is configured"""
    print("=" * 60)
    print("PCCM Faculty Hub - Resend Email Setup Test")
    print("=" * 60)
    print()
    
    if not RESEND_API_KEY:
        print("❌ ERROR: RESEND_API_KEY environment variable not set!")
        print()
        print("Please set it:")
        print("  export RESEND_API_KEY='re_your_api_key_here'")
        print()
        return False
    
    print("✅ Resend API key is configured")
    print(f"   Key starts with: {RESEND_API_KEY[:10]}...")
    print()
    return True


def test_irpa_email():
    """Send test IRPA confirmation email"""
    print("-" * 60)
    print("Testing IRPA Shift Confirmation Email")
    print("-" * 60)
    
    # Get test email from user
    test_email = input("Enter your email address to receive test: ")
    test_name = input("Enter test faculty name (e.g., John Smith): ")
    
    # Generate some test dates
    today = datetime.now()
    test_dates = [
        (today + timedelta(days=7)).strftime("%Y-%m-%d"),
        (today + timedelta(days=14)).strftime("%Y-%m-%d"),
        (today + timedelta(days=21)).strftime("%Y-%m-%d"),
    ]
    
    print()
    print(f"Sending IRPA confirmation to: {test_email}")
    print(f"Test dates: {test_dates}")
    print()
    
    success = send_irpa_confirmation(
        faculty_name=test_name,
        faculty_email=test_email,
        selected_dates=test_dates,
        academic_year="2025-2026"
    )
    
    if success:
        print("✅ IRPA confirmation email sent successfully!")
        print("   Check your inbox (and spam folder)")
    else:
        print("❌ Failed to send IRPA confirmation email")
        print("   Check the logs for details")
    
    print()
    return success


def test_unavailability_email():
    """Send test unavailability confirmation email"""
    print("-" * 60)
    print("Testing Unavailability Request Confirmation Email")
    print("-" * 60)
    
    # Get test email from user
    test_email = input("Enter your email address to receive test: ")
    test_name = input("Enter test faculty name (e.g., John Smith): ")
    
    # Generate some test weeks
    start_date = datetime(2025, 12, 22)  # Week before Christmas
    test_weeks = [
        {
            "week_number": 26,
            "start_date": start_date.strftime("%Y-%m-%d"),
            "end_date": (start_date + timedelta(days=6)).strftime("%Y-%m-%d")
        },
        {
            "week_number": 27,
            "start_date": (start_date + timedelta(days=7)).strftime("%Y-%m-%d"),
            "end_date": (start_date + timedelta(days=13)).strftime("%Y-%m-%d")
        },
    ]
    
    print()
    print(f"Sending unavailability confirmation to: {test_email}")
    print(f"Test weeks: {len(test_weeks)} weeks")
    print()
    
    success = send_unavailability_confirmation(
        faculty_name=test_name,
        faculty_email=test_email,
        selected_weeks=test_weeks,
        academic_year="2025-2026"
    )
    
    if success:
        print("✅ Unavailability confirmation email sent successfully!")
        print("   Check your inbox (and spam folder)")
    else:
        print("❌ Failed to send unavailability confirmation email")
        print("   Check the logs for details")
    
    print()
    return success


def main():
    """Run all email tests"""
    print()
    
    # First check if API key is set
    if not test_email_setup():
        return
    
    print()
    print("Which email type would you like to test?")
    print("1. IRPA Shift Confirmation")
    print("2. Unavailability Request Confirmation")
    print("3. Both")
    print()
    
    choice = input("Enter choice (1-3): ").strip()
    
    print()
    
    if choice == "1":
        test_irpa_email()
    elif choice == "2":
        test_unavailability_email()
    elif choice == "3":
        test_irpa_email()
        print()
        test_unavailability_email()
    else:
        print("Invalid choice")
        return
    
    print()
    print("=" * 60)
    print("Email Testing Complete")
    print("=" * 60)
    print()
    print("If emails didn't arrive:")
    print("1. Check spam/junk folder")
    print("2. Verify sender domain in Resend dashboard")
    print("3. Check Resend Logs for send status")
    print("4. Verify API key is correct")
    print()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nTest cancelled by user")
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
