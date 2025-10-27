# test_gemini.py
"""
AnswerForge Gemini Integration Tester
-------------------------------------
This script verifies that your Gemini 2.5 Pro integration works properly.

Run it using:
    python test_gemini.py

Expected output:
    === Running Gemini test ===
    === Gemini explanation ===
    <Gemini's explanation of the code>
"""

import traceback
import os
from dotenv import load_dotenv

# Load .env file
load_dotenv()

# Check that API key is set
if not os.getenv("GEMINI_API_KEY"):
    raise RuntimeError("❌ GEMINI_API_KEY not found in .env file (no quotes please).")

# Import from your Gemini client
from answerforge.llm.gemini_client import explain_code_with_gemini


def main():
    """
    Runs a quick test of the Gemini client to verify API connectivity and response quality.
    """
    # Sample input for testing
    snippet = "print('Hello, world!')"
    question = "Explain this simple hello world program"

    print("\n=== Running Gemini test ===\n")

    try:
        # Call the Gemini explanation function
        explanation = explain_code_with_gemini(snippet, question)

        print("=== Gemini explanation ===")
        print(explanation)
        print("\n✅ Gemini integration test completed successfully.\n")

    except Exception as e:
        print("\n⚠️ An error occurred while testing Gemini integration:")
        print(f"Error message: {e}")
        print("\n--- Full Traceback ---")
        traceback.print_exc()


if __name__ == "__main__":
    main()

