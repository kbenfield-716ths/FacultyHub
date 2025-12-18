"""
Email notification service for PCCM Faculty Hub
Handles confirmation emails for IRPA shifts and unavailability requests
Uses Resend API (https://resend.com)
"""

import os
from datetime import datetime
from typing import List, Dict
import logging
import resend

logger = logging.getLogger(__name__)

# Email configuration
SENDER_EMAIL = "kbenfield@rekindelingproject.com"
SENDER_NAME = "PCCM Faculty Hub"

# Get Resend API key from environment variable
RESEND_API_KEY = os.getenv("RESEND_API_KEY")

# Set the API key for the resend library
if RESEND_API_KEY:
    resend.api_key = RESEND_API_KEY


def format_date_with_day(date_str: str) -> str:
    """
    Format date string to include day of week
    Input: '2025-12-25' or datetime object
    Output: 'Thursday, December 25, 2025'
    """
    if isinstance(date_str, str):
        date_obj = datetime.strptime(date_str, "%Y-%m-%d")
    else:
        date_obj = date_str
    
    return date_obj.strftime("%A, %B %d, %Y")


def format_date_list(dates: List[str]) -> str:
    """
    Format a list of dates into a nice bulleted list with day of week
    """
    formatted_dates = [f"  • {format_date_with_day(date)}" for date in sorted(dates)]
    return "\n".join(formatted_dates)


def create_irpa_confirmation_email(
    faculty_name: str,
    faculty_email: str,
    selected_dates: List[str],
    academic_year: str
) -> str:
    """
    Create HTML email body for IRPA shift confirmation
    """
    date_count = len(selected_dates)
    date_list = format_date_list(selected_dates)
    
    html_content = f"""
    <html>
    <head>
        <style>
            body {{
                font-family: Arial, sans-serif;
                line-height: 1.6;
                color: #333;
                max-width: 600px;
                margin: 0 auto;
                padding: 20px;
            }}
            .header {{
                background-color: #232D4B;
                color: #E57200;
                padding: 20px;
                text-align: center;
                border-radius: 5px 5px 0 0;
            }}
            .content {{
                background-color: #f9f9f9;
                padding: 20px;
                border: 1px solid #ddd;
                border-radius: 0 0 5px 5px;
            }}
            .dates {{
                background-color: white;
                padding: 15px;
                margin: 15px 0;
                border-left: 4px solid #E57200;
                font-family: monospace;
            }}
            .summary {{
                background-color: #E8F4F8;
                padding: 15px;
                margin: 15px 0;
                border-radius: 5px;
            }}
            .footer {{
                margin-top: 20px;
                padding-top: 20px;
                border-top: 1px solid #ddd;
                font-size: 12px;
                color: #666;
                text-align: center;
            }}
        </style>
    </head>
    <body>
        <div class="header">
            <h2>IRPA Shift Selection Confirmed</h2>
        </div>
        <div class="content">
            <p>Dear Dr. {faculty_name},</p>
            
            <p>This email confirms your IRPA (moonlighting) shift selections for Academic Year {academic_year}.</p>
            
            <div class="summary">
                <strong>Total Nights Selected: {date_count}</strong>
            </div>
            
            <p><strong>Your Selected Dates:</strong></p>
            <div class="dates">
{date_list}
            </div>
            
            <p>These selections have been recorded in the PCCM Faculty Hub system. You can review or modify your selections by logging into the Faculty Hub.</p>
            
            <p>If you have any questions or need to make changes, please contact the scheduling team or access the Faculty Hub at your convenience.</p>
            
            <p>Thank you,<br>
            <strong>PCCM Division Scheduling</strong></p>
        </div>
        <div class="footer">
            <p>This is an automated message from the PCCM Faculty Hub. Please do not reply to this email.</p>
            <p>University of Virginia Health | Division of Pulmonary and Critical Care Medicine</p>
        </div>
    </body>
    </html>
    """
    
    return html_content


def create_unavailability_confirmation_email(
    faculty_name: str,
    faculty_email: str,
    selected_weeks: List[Dict],
    academic_year: str
) -> str:
    """
    Create HTML email body for unavailability request confirmation
    """
    week_count = len(selected_weeks)
    
    # Format weeks with date ranges
    week_list_items = []
    for week in sorted(selected_weeks, key=lambda x: x['week_number']):
        week_num = week['week_number']
        start = format_date_with_day(week['start_date'])
        end = format_date_with_day(week['end_date'])
        week_list_items.append(f"  • Week {week_num}: {start} → {end}")
    
    week_list = "\n".join(week_list_items)
    
    html_content = f"""
    <html>
    <head>
        <style>
            body {{
                font-family: Arial, sans-serif;
                line-height: 1.6;
                color: #333;
                max-width: 600px;
                margin: 0 auto;
                padding: 20px;
            }}
            .header {{
                background-color: #232D4B;
                color: #E57200;
                padding: 20px;
                text-align: center;
                border-radius: 5px 5px 0 0;
            }}
            .content {{
                background-color: #f9f9f9;
                padding: 20px;
                border: 1px solid #ddd;
                border-radius: 0 0 5px 5px;
            }}
            .weeks {{
                background-color: white;
                padding: 15px;
                margin: 15px 0;
                border-left: 4px solid #232D4B;
                font-family: monospace;
                font-size: 14px;
            }}
            .summary {{
                background-color: #E8F4F8;
                padding: 15px;
                margin: 15px 0;
                border-radius: 5px;
            }}
            .warning {{
                background-color: #FFF3CD;
                border-left: 4px solid #FFC107;
                padding: 15px;
                margin: 15px 0;
            }}
            .footer {{
                margin-top: 20px;
                padding-top: 20px;
                border-top: 1px solid #ddd;
                font-size: 12px;
                color: #666;
                text-align: center;
            }}
        </style>
    </head>
    <body>
        <div class="header">
            <h2>Unavailability Request Confirmed</h2>
        </div>
        <div class="content">
            <p>Dear Dr. {faculty_name},</p>
            
            <p>This email confirms your unavailability requests for inpatient service during Academic Year {academic_year}.</p>
            
            <div class="summary">
                <strong>Total Weeks Requested: {week_count}</strong>
            </div>
            
            <p><strong>Your Requested Unavailable Weeks:</strong></p>
            <div class="weeks">
{week_list}
            </div>
            
            <div class="warning">
                <strong>Important Notes:</strong>
                <ul>
                    <li>These are <em>requests</em> for unavailability and are subject to the point-based bidding system</li>
                    <li>Final approval depends on your bid order and available capacity for each week</li>
                    <li>You will receive notification when the final schedule is published</li>
                </ul>
            </div>
            
            <p>You can review or modify your unavailability requests by logging into the PCCM Faculty Hub. Changes can be made until the bidding window closes.</p>
            
            <p>If you have questions about the bidding process or point system, please contact the scheduling team.</p>
            
            <p>Thank you,<br>
            <strong>PCCM Division Scheduling</strong></p>
        </div>
        <div class="footer">
            <p>This is an automated message from the PCCM Faculty Hub. Please do not reply to this email.</p>
            <p>University of Virginia Health | Division of Pulmonary and Critical Care Medicine</p>
        </div>
    </body>
    </html>
    """
    
    return html_content


def send_email(to_email: str, to_name: str, subject: str, html_content: str) -> bool:
    """
    Send email via Resend
    
    Returns:
        bool: True if successful, False otherwise
    """
    if not RESEND_API_KEY:
        logger.error("RESEND_API_KEY environment variable not set")
        return False
    
    try:
        params = {
            "from": f"{SENDER_NAME} <{SENDER_EMAIL}>",
            "to": [to_email],
            "subject": subject,
            "html": html_content,
        }
        
        response = resend.Emails.send(params)
        
        # Resend returns a dict with 'id' on success
        if response and 'id' in response:
            logger.info(f"Email sent successfully to {to_email}: {subject} (ID: {response['id']})")
            return True
        else:
            logger.error(f"Failed to send email to {to_email}. Response: {response}")
            return False
            
    except Exception as e:
        logger.error(f"Error sending email to {to_email}: {str(e)}")
        return False


def send_irpa_confirmation(
    faculty_name: str,
    faculty_email: str,
    selected_dates: List[str],
    academic_year: str
) -> bool:
    """
    Send IRPA shift confirmation email
    
    Args:
        faculty_name: Faculty member's full name
        faculty_email: Faculty member's email address
        selected_dates: List of date strings in YYYY-MM-DD format
        academic_year: e.g., "2025-2026"
    
    Returns:
        bool: True if email sent successfully
    """
    subject = f"IRPA Shift Selection Confirmed - AY {academic_year}"
    html_content = create_irpa_confirmation_email(
        faculty_name, faculty_email, selected_dates, academic_year
    )
    
    return send_email(faculty_email, faculty_name, subject, html_content)


def send_unavailability_confirmation(
    faculty_name: str,
    faculty_email: str,
    selected_weeks: List[Dict],
    academic_year: str
) -> bool:
    """
    Send unavailability request confirmation email
    
    Args:
        faculty_name: Faculty member's full name
        faculty_email: Faculty member's email address
        selected_weeks: List of dicts with 'week_number', 'start_date', 'end_date'
        academic_year: e.g., "2025-2026"
    
    Returns:
        bool: True if email sent successfully
    """
    subject = f"Unavailability Request Confirmed - AY {academic_year}"
    html_content = create_unavailability_confirmation_email(
        faculty_name, faculty_email, selected_weeks, academic_year
    )
    
    return send_email(faculty_email, faculty_name, subject, html_content)
def send_feedback_email(feedback_data: dict) -> bool:
    """
    Send feedback submission email to admin
    
    Args:
        feedback_data: Dictionary containing feedback details
            - user_email: Email of user submitting feedback
            - feedback_text: The feedback content
            - timestamp: When feedback was submitted
    
    Returns:
        bool: True if email sent successfully
    """
    admin_email = "kjm5ul@virginia.edu"
    
    html_content = f"""
    <html>
    <head>
        <style>
            body {{
                font-family: Arial, sans-serif;
                line-height: 1.6;
                color: #333;
                max-width: 600px;
                margin: 0 auto;
                padding: 20px;
            }}
            .header {{
                background-color: #232D4B;
                color: #E57200;
                padding: 20px;
                text-align: center;
                border-radius: 5px 5px 0 0;
            }}
            .content {{
                background-color: #f9f9f9;
                padding: 20px;
                border: 1px solid #ddd;
                border-radius: 0 0 5px 5px;
            }}
            .feedback {{
                background-color: white;
                padding: 15px;
                margin: 15px 0;
                border-left: 4px solid #E57200;
                white-space: pre-wrap;
            }}
            .meta {{
                background-color: #E8F4F8;
                padding: 15px;
                margin: 15px 0;
                border-radius: 5px;
            }}
        </style>
    </head>
    <body>
        <div class="header">
            <h2>Faculty Hub Feedback Received</h2>
        </div>
        <div class="content">
            <div class="meta">
                <p><strong>From:</strong> {feedback_data.get('user_email', 'Anonymous')}</p>
                <p><strong>Submitted:</strong> {feedback_data.get('timestamp', 'Unknown')}</p>
            </div>
            
            <p><strong>Feedback:</strong></p>
            <div class="feedback">
{feedback_data.get('feedback_text', '')}
            </div>
        </div>
    </body>
    </html>
    """
    
    subject = f"Faculty Hub Feedback from {feedback_data.get('user_email', 'User')}"
    
    return send_email(admin_email, "Admin", subject, html_content)
