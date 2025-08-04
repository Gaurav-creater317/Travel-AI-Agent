params = {
    "space_id": "e7a9810d-3897-48b7-b7e8-fc214692ed5b", 
}
def gen_ai_service(context, params = params, **custom):
    # import dependencies
    from langchain_ibm import ChatWatsonx
    from ibm_watsonx_ai import APIClient
    from ibm_watsonx_ai.foundation_models.utils import Tool, Toolkit
    from langchain_core.messages import AIMessage, HumanMessage
    from langgraph.checkpoint.memory import MemorySaver
    from langgraph.prebuilt import create_react_agent
    import json
    import requests
    model = "meta-llama/llama-3-2-90b-vision-instruct"
    service_url = "https://us-south.ml.cloud.ibm.com"
    # Get credentials token
    credentials = {
        "url": service_url,
        "token": context.generate_token()
    }
    # Setup client
    client = APIClient(credentials)
    space_id = params.get("space_id")
    client.set.default_space(space_id)
    def create_chat_model(watsonx_client):
        parameters = {
            "frequency_penalty": 0,
            "max_tokens": 2000,
            "presence_penalty": 0,
            "temperature": 0,
            "top_p": 1
        }
        chat_model = ChatWatsonx(
            model_id=model,
            url=service_url,
            space_id=space_id,
            params=parameters,
            watsonx_client=watsonx_client,
        )
        return chat_model
    def create_utility_agent_tool(tool_name, params, api_client, **kwargs):
        from langchain_core.tools import StructuredTool
        utility_agent_tool = Toolkit(
            api_client=api_client
        ).get_tool(tool_name)
        tool_description = utility_agent_tool.get("description")
        if (kwargs.get("tool_description")):
            tool_description = kwargs.get("tool_description")
        elif (utility_agent_tool.get("agent_description")):
            tool_description = utility_agent_tool.get("agent_description")
        tool_schema = utility_agent_tool.get("input_schema")
        if (tool_schema == None):
            tool_schema = {
                "type": "object",
                "additionalProperties": False,
                "$schema": "http://json-schema.org/draft-07/schema#",
                "properties": {
                    "input": {
                        "description": "input for the tool",
                        "type": "string"
                    }
                }
            }
        def run_tool(**tool_input):
            query = tool_input
            if (utility_agent_tool.get("input_schema") == None):
                query = tool_input.get("input")
            results = utility_agent_tool.run(
                input=query,
                config=params
            )
            return results.get("output")
        return StructuredTool(
            name=tool_name,
            description = tool_description,
            func=run_tool,
            args_schema=tool_schema
        )
    def create_custom_tool(tool_name, tool_description, tool_code, tool_schema, tool_params):
        from langchain_core.tools import StructuredTool
        import ast
        def call_tool(**kwargs):
            tree = ast.parse(tool_code, mode="exec")
            custom_tool_functions = [ x for x in tree.body if isinstance(x, ast.FunctionDef) ]
            function_name = custom_tool_functions[0].name
            compiled_code = compile(tree, 'custom_tool', 'exec')
            namespace = tool_params if tool_params else {}
            exec(compiled_code, namespace)
            return namespace[function_name](**kwargs)
        tool = StructuredTool(
            name=tool_name,
            description = tool_description,
            func=call_tool,
            args_schema=tool_schema
        )
        return tool
    def create_custom_tools():
        custom_tools = []
    def create_tools(inner_client, context):
        tools = []
        config = {
            "maxResults": 10
        }
        tools.append(create_utility_agent_tool("GoogleSearch", config, inner_client))
        config = {
        }
        tools.append(create_utility_agent_tool("DuckDuckGo", config, inner_client))
        config = {
            "maxResults": 5
        }
        tools.append(create_utility_agent_tool("Wikipedia", config, inner_client))
        config = {
        }
        tools.append(create_utility_agent_tool("Weather", config, inner_client))
        config = {
        }
        tools.append(create_utility_agent_tool("WebCrawler", config, inner_client))
        return tools
    def create_agent(model, tools, messages):
        memory = MemorySaver()
        instructions = """
give me about the travel plan related topics only . do not give about programming launguages , academics or any other topics. You can say example - Sorry , i am a travel agent chatbot and can answer travel related queries only.
1. 🎯 Purpose
You are a Travel Planner AI Agent. Your goal is to help users plan their trips efficiently, intelligently, and personally, using real-time data and thoughtful recommendations.
2. 📌 Core Functions
Destination Discovery: Suggest destinations based on user's interests (e.g., beaches, mountains, cultural sites), budget, and travel duration.
Itinerary Creation: Build day-wise travel plans including key places to visit, activities, and rest time. Always consider proximity and local time constraints.
Transport Options: Recommend suitable transportation (flight, train, bus, rental car) based on price, speed, and convenience.
Accommodation Search: Suggest stays such as hotels, hostels, or Airbnb, based on budget, location preference, and ratings.
Local Guides & Maps: Integrate local guides, navigation support, and must-know facts (customs, culture, language tips).
3. 📡 Real-Time Features
Use live data for:
Weather updates
Flight/train schedules
Local events or disruptions
Currency exchange rates
Alert the user in real time about:
Delays or cancellations
Price drops on flights/accommodation
Weather alerts
4. 👤 Personalization
Ask user preferences (budget, dates, travel style, group type).
Remember user constraints (e.g., allergies, mobility issues, visa restrictions).
Tailor recommendations to match these inputs precisely.
5. 📅 Schedule Optimization
Plan activities efficiently by:
Reducing travel time between locations
Accounting for open/close hours of attractions
Allowing reasonable rest, meals, and transition time
6. 💼 Booking & Management
Guide users in:
Booking flights, stays, and activities (link to real platforms if applicable)
Managing booking details (check-in/check-out, boarding times)
Send reminders and allow users to modify bookings as needed.
7. 🤖 Conversational Behavior
Be friendly, clear, and helpful. Use emojis occasionally for warmth 😊.
Ask clarifying questions when user input is incomplete.
Avoid overloading with options — always provide top 3 suggestions with reasons.
8. 🔐 Restrictions
Do not provide financial, legal, or medical advice.
Avoid personal opinions. Keep recommendations data-driven.
Respect privacy. Do not store personal data unless explicitly allowed."""
        for message in messages:
            if message["role"] == "system":
                instructions += message["content"]
        graph = create_react_agent(model, tools=tools, checkpointer=memory, state_modifier=instructions)
        return graph
    def convert_messages(messages):
        converted_messages = []
        for message in messages:
            if (message["role"] == "user"):
                converted_messages.append(HumanMessage(content=message["content"]))
            elif (message["role"] == "assistant"):
                converted_messages.append(AIMessage(content=message["content"]))
        return converted_messages
    def generate(context):
        payload = context.get_json()
        messages = payload.get("messages")
        inner_credentials = {
            "url": service_url,
            "token": context.get_token()
        }
        inner_client = APIClient(inner_credentials)
        model = create_chat_model(inner_client)
        tools = create_tools(inner_client, context)
        agent = create_agent(model, tools, messages)
        generated_response = agent.invoke(
            { "messages": convert_messages(messages) },
            { "configurable": { "thread_id": "42" } }
        )
        last_message = generated_response["messages"][-1]
        generated_response = last_message.content
        execute_response = {
            "headers": {
                "Content-Type": "application/json"
            },
            "body": {
                "choices": [{
                    "index": 0,
                    "message": {
                       "role": "assistant",
                       "content": generated_response
                    }
                }]
            }
        }
        return execute_response
    def generate_stream(context):
        print("Generate stream", flush=True)
        payload = context.get_json()
        headers = context.get_headers()
        is_assistant = headers.get("X-Ai-Interface") == "assistant"
        messages = payload.get("messages")
        inner_credentials = {
            "url": service_url,
            "token": context.get_token()
        }
        inner_client = APIClient(inner_credentials)
        model = create_chat_model(inner_client)
        tools = create_tools(inner_client, context)
        agent = create_agent(model, tools, messages)
        response_stream = agent.stream(
            { "messages": messages },
            { "configurable": { "thread_id": "42" } },
            stream_mode=["updates", "messages"]
        )
        for chunk in response_stream:
            chunk_type = chunk[0]
            finish_reason = ""
            usage = None
            if (chunk_type == "messages"):
                message_object = chunk[1][0]
                if (message_object.type == "AIMessageChunk" and message_object.content != ""):
                    message = {
                        "role": "assistant",
                        "content": message_object.content
                    }
                else:
                    continue
            elif (chunk_type == "updates"):
                update = chunk[1]
                if ("agent" in update):
                    agent = update["agent"]
                    agent_result = agent["messages"][0]
                    if (agent_result.additional_kwargs):
                        kwargs = agent["messages"][0].additional_kwargs
                        tool_call = kwargs["tool_calls"][0]
                        if (is_assistant):
                            message = {
                                "role": "assistant",
                                "step_details": {
                                    "type": "tool_calls",
                                    "tool_calls": [
                                        {
                                            "id": tool_call["id"],
                                            "name": tool_call["function"]["name"],
                                            "args": tool_call["function"]["arguments"]
                                        }
                                    ] 
                                }
                            }
                        else:
                            message = {
                                "role": "assistant",
                                "tool_calls": [
                                    {
                                        "id": tool_call["id"],
                                        "type": "function",
                                        "function": {
                                            "name": tool_call["function"]["name"],
                                            "arguments": tool_call["function"]["arguments"]
                                        }
                                    }
                                ]
                            }
                    elif (agent_result.response_metadata):
                        # Final update
                        message = {
                            "role": "assistant",
                            "content": agent_result.content
                        }
                        finish_reason = agent_result.response_metadata["finish_reason"]
                        if (finish_reason): 
                            message["content"] = ""
                        usage = {
                            "completion_tokens": agent_result.usage_metadata["output_tokens"],
                            "prompt_tokens": agent_result.usage_metadata["input_tokens"],
                            "total_tokens": agent_result.usage_metadata["total_tokens"]
                        }
                elif ("tools" in update):
                    tools = update["tools"]
                    tool_result = tools["messages"][0]
                    if (is_assistant):
                        message = {
                            "role": "assistant",
                            "step_details": {
                                "type": "tool_response",
                                "id": tool_result.id,
                                "tool_call_id": tool_result.tool_call_id,
                                "name": tool_result.name,
                                "content": tool_result.content
                            }
                        }
                    else:
                        message = {
                            "role": "tool",
                            "id": tool_result.id,
                            "tool_call_id": tool_result.tool_call_id,
                            "name": tool_result.name,
                            "content": tool_result.content
                        }
                else:
                    continue
            chunk_response = {
                "choices": [{
                    "index": 0,
                    "delta": message
                }]
            }
            if (finish_reason):
                chunk_response["choices"][0]["finish_reason"] = finish_reason
            if (usage):
                chunk_response["usage"] = usage
            yield chunk_response
    return generate, generate_stream