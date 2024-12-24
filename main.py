import argparse
import ai_integration.claude_client
import game_interface.game_interface
from simple_logger.logger import SimpleLogger


LOGGER = SimpleLogger(__name__, log_file="main.log")

MAX_STEPS = 25

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
    parser.add_argument('-ll', '--log-level', type=str, choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"], default="INFO", help='Set the logging level')
    args = parser.parse_args()

    # Setup logger giving input log level
    log_level = SimpleLogger.parse_log_level(args.log_level)
    SimpleLogger.setup_root_logger(log_level)

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


    prompt = f"""\
             We are in the training grounds to test our flight abilities. \
             You will be responsible for evaluating the state when necessary and performing actions based on the tools provided. \
             You are given {MAX_STEPS} steps maximum to work with in this stage. Let's begin by confirming knowledge of the controls. \
             Engage the enemy aircraft and use any means necessary to eliminate it. There are several enemies, search and destroy at least two.
             Begin by taking a screenshot and responding with a command. \
             When you are finished, complete the mission. \
             You should use a tool with each response. \
             """
    
    next_tool_set = ai_client.send_prompt_to_claude(prompt)
    LOGGER.debug(f"Claude's tool response: {next_tool_set}")

    # While we should continue, execute tools and re prompt claude
    loop_limit = MAX_STEPS
    for _ in range(loop_limit + 1):
        if not ai_client.to_continue_flying():
            break

        execution_results = ai_client.execute_tools()

        # Send results of tool execution back for next steps
        prompt_content = []
        for result in execution_results:
            prompt_content.append(result)

        # If there is no content added, a tool wasn't used.
        # Claude should always use a tool. If the objective is fulfilled it should be stop_flying.
        # If it is just waiting it should be no-op
        if prompt_content == []:
            affirming_response = {
                "type": "text",
                "text": """\
                           You must use a tool in your response.\
                           If you have completed the mission/objective, use the stop_flying tool.\
                           If you are waiting to act on something, use no-op. You should succintly explain what you are waiting to make a decision on.\
                           """
            }
            prompt_content.append(affirming_response)
        
        LOGGER.debug(f"Prompt content: {prompt_content}")
        ai_client.send_prompt_to_claude(prompt_content)
        ai_client.clear_results()
    

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        LOGGER.error(f"A critical error occurred: {e}")
        raise e
