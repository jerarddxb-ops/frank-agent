import anthropic
import requests
import datetime
from calendar_tool import book_meeting, check_availability

client = anthropic.Anthropic(api_key="")
today = datetime.datetime.now()

today = datetime.datetime.now()

system = f"""
Today's date is {today.strftime('%A, %d %B %Y')}.
Current time is {today.strftime('%H:%M')} South African time.
Timezone: Africa/Johannesburg.

You are Frank, a professional, friendly and efficient assistant for Jerard's drone business, The Overview Effect.

Your role is to answer customer questions about drone services, pricing and bookings.

Jerard's equipment:
- DJI Mavic 2 Pro
- 4K video up to 30fps

Pricing:
- Half day: R5000
- Full day: R8000

Do not use emojis.

Always encourage customers to schedule a free 30-minute discovery call with Jerard before confirming any drone project.

The discovery call and the customer's drone project are NOT the same thing. Never confuse the project date with the discovery call date. Always treat them as separate dates.

Discovery calls:
- Are always 30 minutes.
- Should always be booked as soon as reasonably possible.
- May only be booked Tuesday to Friday.
- Jerard has no availability on Mondays.
- Must take place between 09:00 and 16:00 South African time.
- Morning means 09:00-12:00.
- Afternoon means 12:00-16:00.
- Always use the check_availability tool to determine the earliest available meeting time. Never invent or assume availability.
- Never book outside business hours.
- Never book on a Monday.

If a customer requests a Monday, explain that Jerard has no availability on Mondays and immediately offer the earliest available time on Tuesday.

Never simply say "morning" or "afternoon". Always state the exact proposed meeting date and time, for example: "Tuesday 7 July at 09:00 South African time."

When a customer wants to book a discovery call:

1. Ask for ALL of the following in ONE message:
- Full name
- Email address
- Brief project description
- Project date (if known)
- Preferred discovery call date
- Whether they prefer morning or afternoon

2. Once they reply, repeat their email address back exactly and ask them to confirm it is correct. Do not continue until they have confirmed their email.

3. After the email has been confirmed, choose the earliest suitable 30-minute meeting time between 09:00 and 16:00 on their preferred discovery call date. If they requested morning, choose the earliest available morning time. If they requested afternoon, choose the earliest available afternoon time.

4. Tell the customer the EXACT proposed meeting date and time and ask them to confirm it before booking. For example: "I can book your discovery call for Thursday 9 July at 14:00 South African time. Please confirm that you'd like me to book this."

5. Only use the book_meeting tool after the customer has explicitly confirmed BOTH their email address and the exact meeting date and time.

Never use the customer's project date as the meeting date. Always make it clear which date is the project date and which date is the discovery call.Before booking any discovery call, ALWAYS use the check_availability tool.

Never invent an available meeting time.

The check_availability tool returns the earliest available 30-minute slot.

Tell the customer the exact available date and time returned by the tool.

Wait for the customer to confirm the proposed time.

Only then use the book_meeting tool.
"""

tools = [
    {
        "name": "get_weather",
        "description": "Gets the current weather for a given city. Use this when a customer asks about weather conditions.",
        "input_schema": {
            "type": "object",
            "properties": {
                "city": {
                    "type": "string",
                    "description": "The name of the city"
                }
            },
            "required": ["city"]
        }
    },
    {
        "name": "book_meeting",
        "description": "Books a confirmed 30-minute Google Meet discovery call. Only use this tool after the customer has confirmed their email address and explicitly confirmed the exact discovery call date and time. preferred_datetime must be the discovery call date and time in YYYY-MM-DD HH:MM format, never the customer's project date. Meetings may only be booked between 09:00 and 16:00 South African time and never on a Monday.",
        "input_schema": {
            "type": "object",
            "properties": {
                "customer_name": {
                    "type": "string",
                    "description": "Customer's full name"
                },
                "customer_email": {
                    "type": "string",
                    "description": "Customer's confirmed email address"
                },
                "project_description": {
                    "type": "string",
                    "description": "Brief description of the customer's drone project"
                },
                "preferred_datetime": {
                    "type": "string",
                    "description": "Confirmed discovery call date and time in YYYY-MM-DD HH:MM format"
                }
            },
            "required": [
                "customer_name",
                "customer_email",
                "project_description",
                "preferred_datetime"
            ]
        }
    }, {
    "name": "check_availability",
    "description": "Checks Google Calendar and returns the earliest available 30-minute slot for a given date and preference (morning/afternoon).",
    "input_schema": {
        "type": "object",
        "properties": {
            "date": {
                "type": "string",
                "description": "Date in YYYY-MM-DD format"
            },
            "preference": {
                "type": "string",
                "description": "morning or afternoon"
            }
        },
        "required": ["date", "preference"]
    }
}
]

def get_weather(city):
    url = f"https://wttr.in/{city}?format=3"
    response = requests.get(url)
    return response.text

def handle_tool_call(tool_name, tool_input):
    if tool_name == "get_weather":
        return get_weather(tool_input["city"])

    elif tool_name == "check_availability":
        slot = check_availability(
            tool_input["date"],
            tool_input["preference"]
        )

        if slot:
            return slot

        return "No availability."

    elif tool_name == "book_meeting":
        dt = datetime.datetime.strptime(
            tool_input["preferred_datetime"],
            "%Y-%m-%d %H:%M"
        )

        # No Mondays
        if dt.weekday() == 0:
            return "Discovery calls cannot be booked on Mondays. Please choose another weekday."

        # Business hours: 09:00 - 16:00
        if dt.hour < 9 or dt.hour >= 16:
            return "Discovery calls can only be booked between 09:00 and 16:00 South African time."

        try:
            return book_meeting(
                summary=f"Discovery Call - {tool_input['customer_name']}",
                description=(
                    f"Customer: {tool_input['customer_name']}\n"
                    f"Email: {tool_input['customer_email']}\n\n"
                    f"Project:\n{tool_input['project_description']}"
                ),
                attendee_email=tool_input["customer_email"],
                start_time=dt
            )
        except Exception as e:
            return f"Booking failed: {str(e)}"

    else:
        return f"Unknown tool: {tool_name}"

conversation_history = []

while True:
    user_input = input("You: ")
    conversation_history.append({"role": "user", "content": user_input})

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1024,
        system=system,
        tools=tools,
        messages=conversation_history
    )

    if response.stop_reason == "tool_use":
        tool_results = []

        for block in response.content:
            if block.type == "tool_use":
                result = handle_tool_call(block.name, block.input)

                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": str(result)
        })

        conversation_history.append({
            "role": "assistant",
            "content": response.content
        })

        conversation_history.append({
            "role": "user",
            "content": tool_results
})
        final_response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=1024,
            system=system,
            tools=tools,
            messages=conversation_history
        )
        reply = final_response.content[0].text
    else:
        reply = response.content[0].text

    conversation_history.append({"role": "assistant", "content": reply})
    print("Frank: " + reply)