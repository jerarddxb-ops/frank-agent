import datetime
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
import os

SCOPES = ['https://www.googleapis.com/auth/calendar']

def get_calendar_service():
    creds = None
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file('googlecredentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        with open('token.json', 'w') as token:
            token.write(creds.to_json())
    return build('calendar', 'v3', credentials=creds)

def book_meeting(summary, description, attendee_email, start_time, duration_minutes=30):
    service = get_calendar_service()
    
    end_time = start_time + datetime.timedelta(minutes=duration_minutes)
    
    event = {
        'summary': summary,
        'description': description,
        'start': {'dateTime': start_time.isoformat(), 'timeZone': 'Africa/Johannesburg'},
        'end': {'dateTime': end_time.isoformat(), 'timeZone': 'Africa/Johannesburg'},
        'attendees': [{'email': attendee_email}],
        'conferenceData': {
            'createRequest': {
                'requestId': f"frank-{start_time.timestamp()}",
                'conferenceSolutionKey': {'type': 'hangoutsMeet'}
            }
        }
    }
    
    event = service.events().insert(
        calendarId='primary',
        body=event,
        conferenceDataVersion=1,
        sendUpdates='all'
    ).execute()
    
    meet_link = event.get('hangoutLink', 'No Meet link generated')
    return f"Meeting booked! Google Meet link: {meet_link}"
from zoneinfo import ZoneInfo

def check_availability(date_str, preference):
    service = get_calendar_service()

    tz = ZoneInfo("Africa/Johannesburg")

    date = datetime.datetime.strptime(date_str, "%Y-%m-%d").date()

    if preference.lower() == "morning":
        start_hour = 9
        end_hour = 12
    else:
        start_hour = 12
        end_hour = 16

    for hour in range(start_hour, end_hour):
        for minute in [0, 30]:

            start = datetime.datetime.combine(
                date,
                datetime.time(hour, minute),
                tzinfo=tz
            )

            end = start + datetime.timedelta(minutes=30)

            events = service.events().list(
                calendarId="primary",
                timeMin=start.isoformat(),
                timeMax=end.isoformat(),
                singleEvents=True
            ).execute()

            if len(events["items"]) == 0:
                return start.strftime("%Y-%m-%d %H:%M")

    return None
if __name__ == "__main__":
    result = book_meeting(
        summary="Test Meeting with Frank",
        description="This is a test booking from Frank the agent",
        attendee_email="test@example.com",
        start_time=datetime.datetime.now() + datetime.timedelta(hours=1)
    )
    print(result)