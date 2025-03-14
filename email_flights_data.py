import os
import json
import smtplib
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv

load_dotenv()

class EmailFlightData:
  def send_mail(self, recipient_email, subject, content):
    """
    Send an email to the recipient_email with the given subject and content.
    """
    smtp_server = os.getenv("SMTP_SERVER")
    smtp_port = os.getenv("SMTP_PORT")
    email_address = os.getenv("EMAIL_ADDRESS")
    email_password = os.getenv("EMAIL_PASSWORD")

    message = MIMEMultipart()
    message["From"] = email_address
    message["To"] = recipient_email
    message["Subject"] = subject
    message.attach(MIMEText(content, "html"))

    try:
      with smtplib.SMTP(smtp_server, smtp_port) as server:
        server.starttls()
        server.login(email_address, email_password)
        server.sendmail(email_address, recipient_email, message.as_string())
        print("Email sent successfully.")

        return True
    except Exception as e:
      print(f"Error sending email: {e}")
      return False
    
  def format_email_content(self, best_sequence, best_itinerary):
      """Format the flight itinerary data into an HTML email."""
      flight_sequence = " → ".join(best_sequence)
      print(flight_sequence)
      best_itinerary = json.loads(best_itinerary)
      
      flight_details = []
      for flight in best_itinerary["flights"]:
        departure_time = datetime.strptime(flight["departure_time"], "%Y-%m-%dT%H:%M:%S%z")
        arrival_time = datetime.strptime(flight["arrival_time"], "%Y-%m-%dT%H:%M:%S%z")

        flight_details.append(f"""
        <li>
            <strong>{flight['airline']} {flight['flight_number']}</strong><br>
            <strong>Departure:</strong> {departure_time.strftime('%Y-%m-%d %H:%M:%S')} ({flight['origin']})<br>
            <strong>Arrival:</strong> {arrival_time.strftime('%Y-%m-%d %H:%M:%S')} ({flight['destination']})<br>
            <strong>Duration:</strong> {flight['duration']}<br>
            <strong>Cost:</strong> ${flight['cost']:.2f}<br>
            <strong>Layover:</strong> {flight['layover']} at {flight['layover_iata']}<br>
        </li>
        """)

      summary = f"""
        <ul>
            <li><strong>Total Flight Duration:</strong> {str(best_itinerary['total_flight_duration'])}</li>
            <li><strong>Total Layover Duration:</strong> {str(best_itinerary['total_layover_duration'])}</li>
            <li><strong>Total Travel Time:</strong> {str(best_itinerary['total_travel_time'])}</li>
            <li><strong>Total Cost:</strong> ${best_itinerary['total_cost']:.2f}</li>
        </ul>
        """
      
      content = f"""
        <h1>Flight Itinerary</h1>
        <h2>Flight Sequence</h2>
        <p>{flight_sequence}</p>

        <h2>Flight Details</h2>
        <ul>{''.join(flight_details)}</ul>

        <h2>Summary</h2>
        {summary}
        """
      return content