import argparse
import ai_integration.claude_client
import game_interface.game_interface
from simple_logger.logger import SimpleLogger

LOGGER = SimpleLogger(__name__, log_file="main.log")

def main():
    model_input_choices = [
        ["0-0", "dev-0", "gemini", "free"],
        ['0-1', "dev-1", "claude-3.5-haiku", "cheap"],
        ['1', "stable", "claude-3.5-sonnet", "pricy"],
        ['2', "prod", "claude-3-opus", "expensive"],
    ]
    model_choices_flat = [opt for choice_series in model_input_choices for opt in choice_series]
    parser = argparse.ArgumentParser(description='Run the game with a specified model.')
    parser.add_argument('-m', '--model', type=str, choices=model_choices_flat, help='Model to use (0: dev, 1: stable, 2: prod)')
    args = parser.parse_args()

    input_model = args.model
    if input_model is None:
        while True:
            input_model = input(f"Select model ({model_choices_flat})")
            if input_model in [model_opt for model_opt in model_input_choices]:
                break
            else:
                print(f"Invalid model selection: {input_model}")

    (sonnet, haiku, opus) = ai_integration.claude_client.fetchModels()
    models = {
       # Claude 3.5 Haiku aliases
       "claude-3.5-haiku": {
           "aliases": ["dev-1", "cheap", "0-1"],
           "model_name": haiku.id
       },
       
       # Claude 3.5 Sonnet aliases
       "claude-3-5-sonnet": {
           "aliases": ["stable", "pricy", "1"],
           "model_name": sonnet.id
       },
       
       # Claude 3 Opus aliases
       "claude-3-opus": {
           "aliases": ["prod", "expesnive", "2"],
           "model_name": opus.id
       },

       "gemini": {
           "aliases": ["dev-0", "free", "0-0"],
           "model_name": "gemini-2.0-flash"
       }
    
   }
   
    # Create a reverse lookup dictionary for easier access
    model_lookup = {}
    for model_key, info in models.items():
       model_lookup[model_key] = info["model_name"]
       for alias in info["aliases"]:
           model_lookup[alias] = info["model_name"]
    
    selected_model = model_lookup.get(input_model)
    ai_client = ai_integration.claude_client.ClaudeClient(selected_model)
    LOGGER.debug(f"Client model: {ai_client.model}")

    
    prompt = """
             This first run is a test run. You should take a screenshot of the game and describe the game state.
             Once that is done, finish flying.
             """
    
    next_tool_set = ai_client.send_prompt_to_claude(prompt)
    LOGGER.debug(f"Claude's tool response: {next_tool_set}")

    # While we should continue, execute tools and re prompt claude
    loop_limit = 3
    for _ in range(loop_limit + 1):
        if not ai_client.to_continue_flying():
            break

        execution_results = ai_client.execute_tools()

        # Send results of tool execution back for next steps
        prompt_content = []
        for result in execution_results:
            prompt_content.append(result)
        
        LOGGER.debug(f"Prompt content: {prompt_content}")
        ai_client.send_prompt_to_claude(prompt_content)
        ai_client.clear_results()
    

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        LOGGER.error(f"A critical error occurred: {e}")
        raise e
