from flask import Flask, request, jsonify
import anthropic
import requests
import datetime
from calendar_tool import book_meeting, check_availability
import os
app = Flask(__name__)

client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

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

If a customer requests a Monday, suggest another day that week without mentioning that Mondays are unavailable.

Never simply say "morning" or "afternoon". Always state the exact proposed meeting date and time.

When a customer wants to book a discovery call, ask for all of the following in ONE message: full name, email address, brief project description, project date (if known), and whether they prefer morning or afternoon.

Once they reply, repeat their email address back exactly and ask them to confirm it is correct. Do not continue until they have confirmed their email.

After the email is confirmed, use check_availability to find the earliest suitable slot. Tell the customer the exact proposed date and time and ask them to confirm before booking.

Only use the book_meeting tool after the customer has explicitly confirmed both their email and the exact meeting time.
"""

tools = [
    {
        "name": "get_weather",
        "description": "Gets the current weather for a given city.",
        "input_schema": {
            "type": "object",
            "properties": {"city": {"type": "string", "description": "The city name"}},
            "required": ["city"]
        }
    },
    {
        "name": "book_meeting",
        "description": "Books a confirmed 30-minute Google Meet discovery call.",
        "input_schema": {
            "type": "object",
            "properties": {
                "customer_name": {"type": "string"},
                "customer_email": {"type": "string"},
                "project_description": {"type": "string"},
                "preferred_datetime": {"type": "string", "description": "YYYY-MM-DD HH:MM"}
            },
            "required": ["customer_name", "customer_email", "project_description", "preferred_datetime"]
        }
    },
    {
        "name": "check_availability",
        "description": "Checks Google Calendar and returns the earliest available 30-minute slot.",
        "input_schema": {
            "type": "object",
            "properties": {
                "date": {"type": "string", "description": "YYYY-MM-DD"},
                "preference": {"type": "string", "description": "morning or afternoon"}
            },
            "required": ["date", "preference"]
        }
    }
]

def get_weather(city):
    return requests.get(f"https://wttr.in/{city}?format=3").text

def handle_tool_call(tool_name, tool_input):
    if tool_name == "get_weather":
        return get_weather(tool_input["city"])
    elif tool_name == "check_availability":
        slot = check_availability(tool_input["date"], tool_input["preference"])
        return slot if slot else "No availability."
    elif tool_name == "book_meeting":
        dt = datetime.datetime.strptime(tool_input["preferred_datetime"], "%Y-%m-%d %H:%M")
        if dt.weekday() == 0:
            return "Discovery calls cannot be booked on Mondays."
        if dt.hour < 9 or dt.hour >= 16:
            return "Discovery calls can only be booked between 09:00 and 16:00."
        try:
            return book_meeting(
                summary=f"Discovery Call - {tool_input['customer_name']}",
                description=f"Customer: {tool_input['customer_name']}\nEmail: {tool_input['customer_email']}\n\nProject:\n{tool_input['project_description']}",
                attendee_email=tool_input["customer_email"],
                start_time=dt
            )
        except Exception as e:
            return f"Booking failed: {str(e)}"
    return f"Unknown tool: {tool_name}"

@app.route("/chat", methods=["POST"])
def chat():
    data = request.json
    conversation_history = data.get("messages", [])

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
                tool_results.append({"type": "tool_result", "tool_use_id": block.id, "content": str(result)})

        conversation_history.append({"role": "assistant", "content": response.content})
        conversation_history.append({"role": "user", "content": tool_results})

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
    return jsonify({"reply": reply, "messages": conversation_history})

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)