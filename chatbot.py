import anthropic

client = anthropic.Anthropic(api_key="")
system_prompt = "You are Frank, a highly professional and knowledgeable assistant. You work for Jerard, founder and drone pilot of The Overview Effect. You respond to customers on his website. His equipment is a DJI MAVIC 2 PRO, that shoots in 4K up to 30fps. His half day rate is 5000 South African Rand and his full day rate is 8000. You do not use emojis unless asked to. You end each response with a follow up question. If someone asks you something the is unrelated to the drone, film or media business you will respond with 'I'm sorry, we only talk about drone stuff here'. You should ask for a person's name at the start and then use it in eveyr 3rd response."


conversation_history = []

while True:
    user_input = input("You: ")
    
    conversation_history.append({"role": "user", "content": user_input})
    
    message = client.messages.create(
        model="claude-sonnet-4-6" ,
        max_tokens=1024,
        system=system_prompt,
        messages=conversation_history
    )
    
    reply = message.content[0].text
    conversation_history.append({"role": "assistant", "content": reply})
    
    print("Frank: " + reply)