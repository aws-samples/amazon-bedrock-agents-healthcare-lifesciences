def get_named_parameter(event, name):
    if name not in event:
        return None

    return event.get(name)


def lambda_handler(event, context):
    print(f"Event: {event}")
    print(f"Context: {context}")

    extended_tool_name = context.client_context.custom["bedrockAgentCoreToolName"]
    resource = extended_tool_name.split("___")[1]

    print(resource)

    if resource == "echo_message":
        message = get_named_parameter(event=event, name="message")

        if not message:
            return {
                "statusCode": 400,
                "body": "❌ Please provide message",
            }

        try:
            response = echo_message(message=message) 
        except Exception as e:
            print(e)
            return {
                "statusCode": 400,
                "body": f"❌ {e}",
            }

        return {
            "statusCode": 200,
            "body": f"👤 Message echo: {response}",
        }

    
    return {
        "statusCode": 400,
        "body": f"❌ Unknown toolname: {resource}",
    }


def echo_message(message: str) -> str:
    """
    Echo back the provided message.
    
    Args:
        message: The message to echo back
        
    Returns:
        The same message that was provided
    """
    return f"Echo: {message}"