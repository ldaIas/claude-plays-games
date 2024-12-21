import anthropic
import game_interface.game_interface
import os

class ClaudeClient:
    def __init__(self):
        self.api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise ValueError("ANTHROPIC_API_KEY environment variable is required.")
        self.anthropic = anthropic.Anthropic(api_key=self.api_key)
        self.tools = [
            {
                "name": "take_screenshot",
                "description": "Takes a screenshot of the current game view.",
                "parameters": [
                    {
                        "name": "filename",
                        "type": "string",
                        "description": "The name to save the screenshot as (e.g., 'metrics.png'). Optional, defaults to 'screenshot.png'."
                    }
                ]
            },
            {
                "name": "press_key",
                "description": "Presses and releases a specified keyboard key.",
                "parameters": [
                    {
                        "name": "key",
                        "type": "string",
                        "description": "The key to press (e.g., 'w', 's', 'a', 'd', 'Space')."
                    }
                ]
            },
            {
                "name": "hold_key",
                "description": "Holds down a specified keyboard key for a certain duration.",
                "parameters": [
                    {
                        "name": "key",
                        "type": "string",
                        "description": "The key to hold down (e.g., 'w', 's')."
                    },
                    {
                        "name": "duration",
                        "type": "number",
                        "description": "The duration in seconds to hold the key down."
                    }
                ]
            },
            {
                "name": "move_mouse",
                "description": "Moves the mouse cursor to specific coordinates on the screen.",
                "parameters": [
                    {
                        "name": "x",
                        "type": "integer",
                        "description": "The x-coordinate to move the mouse to."
                    },
                    {
                        "name": "y",
                        "type": "integer",
                        "description": "The y-coordinate to move the mouse to."
                    }
                ]
            },
            {
                "name": "click_mouse",
                "description": "Clicks a mouse button.",
                "parameters": [
                    {
                        "name": "button",
                        "type": "string",
                        "description": "The mouse button to click ('left', 'right', or 'middle'). Optional, defaults to 'left'."
                    }
                ]
            }
        ]

    def execute_tool(self, tool_name, parameters):
        print(f"Executing tool: {tool_name} with parameters: {parameters}")
        if tool_name == "take_screenshot":
            game_interface.take_screenshot(**parameters)
        elif tool_name == "press_key":
            game_interface.press_key(**parameters)
        elif tool_name == "hold_key":
            game_interface.hold_key(**parameters)
        elif tool_name == "move_mouse":
            game_interface.move_mouse(**parameters)
        elif tool_name == "click_mouse":
            game_interface.click_mouse(**parameters)
        else:
            return f"Tool '{tool_name}' not found."
        return "Tool executed successfully."

    def send_prompt_to_claude(self, prompt):
        tool_descriptions = [{
            "name": tool["name"],
            "description": tool["description"],
            "parameters": tool["parameters"]
        } for tool in self.tools]

        response = self.anthropic.messages.create(
            model="claude-3-opus-20240229",
            max_tokens=1024,
            messages=[
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            tools=tool_descriptions
        )
        return response

def get_tool_descriptions():
    client = ClaudeClient()
    return [
        {"name": tool["name"], "description": tool["description"], "parameters": tool["parameters"]}
        for tool in client.tools
    ]

if __name__ == "__main__":
    tool_descriptions = get_tool_descriptions()
    print("Available tools:")
    for tool in tool_descriptions:
        print(f"- {tool['name']}: {tool['description']}")
        if tool['parameters']:
            print("  Parameters:")
            for param in tool['parameters']:
                print(f"    - {param['name']} ({param['type']}): {param['description']}")
        print()

    claude_client = ClaudeClient()
    prompt = "Take a screenshot of the current game view and save it as 'initial_view.png'."
    response = claude_client.send_prompt_to_claude(prompt)
    print(f"Claude's response: {response}")
