"""Command-line interface for the payment collection agent."""

from src.agent import Agent


def main():
    """Run interactive CLI for the agent."""
    print("=" * 60)
    print("Payment Collection Agent - Interactive CLI")
    print("=" * 60)
    print("Type 'quit' or 'exit' to end the conversation\n")
    
    agent = Agent()
    
    # Start the conversation
    response = agent.next("Hi")
    print(f"Agent: {response['message']}\n")
    
    while True:
        try:
            user_input = input("You: ").strip()
            
            if not user_input:
                continue
            
            if user_input.lower() in ['quit', 'exit', 'bye']:
                print("\nGoodbye!")
                break
            
            response = agent.next(user_input)
            print(f"\nAgent: {response['message']}\n")
            
            # Check if session has ended
            if agent.state.current_state.value == "TERMINATED":
                print("Session ended. Goodbye!")
                break
        
        except KeyboardInterrupt:
            print("\n\nSession interrupted. Goodbye!")
            break
        except Exception as e:
            print(f"\nError: {e}")
            print("Please try again or restart the session.\n")


if __name__ == "__main__":
    main()
