# ERPNext Gemini Integration

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

Integrate Google's Gemini AI models into your ERPNext instance to enhance workflows, automate tasks, and gain insights from your data.

This app provides a framework for leveraging Gemini's capabilities, including natural language processing, multi-modal understanding (text, images, PDFs), function calling, and grounding with Google Search, directly within ERPNext.

## Features

*   **Gemini Chat Widget:** A persistent chat interface available across ERPNext (Desk and Web) for interacting with Gemini.
*   **Multi-modal Input:** Send text prompts along with attached files (PDF, CSV, TXT, JPG, PNG) for analysis or context.
*   **Document Analysis:** Dedicated API endpoint to analyze specific documents stored in ERPNext.
*   **Function Calling:** Define custom functions (via `Gemini Function` DocType) that Gemini can call to interact with ERPNext data or perform actions (e.g., fetch data, create documents, trigger workflows).
*   **Conversation History:** Stores and retrieves conversation history for context-aware interactions.
*   **Configurable Settings:** Manage API keys, select Gemini models (Pro, Vision, Flash), set safety thresholds, control token limits, and toggle features via `Gemini Assistant Settings`.
*   **Audit & Feedback:** Logs interactions (`Gemini Audit Log`, `Gemini Message`) and allows users to provide feedback (`Gemini Feedback`).
*   **Workflow Integration Hooks:** Includes basic hooks for triggering analysis or actions on document submission or via scheduled tasks (requires further implementation).

## Installation

1.  **Download the App:**
    ```bash
    bench get-app https://github.com/Al-Aswany/erpnext_gemini_integration.git
    ```
2.  **Install the App:**
    ```bash
    bench --site [your-site-name] install-app erpnext_gemini_integration
    ```
3.  **Migrate Database:**
    ```bash
    bench --site [your-site-name] migrate
    ```
4.  **Restart Bench:**
    ```bash
    bench restart
    ```

## Setup & Configuration

1.  **Obtain a Gemini API Key:** Get your API key from [Google AI Studio](https://aistudio.google.com/app/apikey).
2.  **Configure Settings in ERPNext:**
    *   Navigate to `Awesome Bar > Gemini Assistant Settings`.
    *   Enter your **Gemini API Key**.
    *   Select the desired **Gemini Model** (e.g., `gemini-1.5-pro-latest`).
    *   Adjust **Model Settings** (Max Tokens, Temperature) if needed.
    *   Configure **Safety Settings** (JSON format) or leave default.
    *   Enable/disable **Features** (Grounding, Function Calling, File Analysis).
    *   Set the **Default Access Role** required to use the assistant.
    *   Save the settings.

## Usage Examples

*   **Chat Widget:** Click the robot icon (usually bottom-right) to open the chat. Ask questions, provide context, or attach files.
    *   "Summarize the attached sales report PDF."
    *   "What are the key points in this text file?"
    *   "Based on the attached image, describe the product."
*   **Function Calling (Requires Defined Functions):**
    *   "What is the stock level for item 'XYZ-123'?"
    *   "Create a draft lead for 'ABC Corp' with contact 'John Doe'."
    *   "Show me my overdue tasks."

## Defining Custom Functions

1.  Navigate to `Awesome Bar > Gemini Function > New`.
2.  **Name:** A unique identifier for the function (e.g., `get_stock_level`).
3.  **Description:** A clear explanation of what the function does, used by Gemini to understand when to call it.
4.  **Parameters (JSON Schema):** Define the input parameters the function expects in [JSON Schema format](https://json-schema.org/).
    *   Example for `get_stock_level`:
        ```json
        {
          "type": "object",
          "properties": {
            "item_code": {
              "type": "string",
              "description": "The unique code of the item to check stock for."
            }
          },
          "required": ["item_code"]
        }
        ```
5.  **Enabled:** Check this box to make the function available to Gemini.
6.  **Implementation:** You will need to modify the backend code (e.g., in `gemini_wrapper.py` or a dedicated module) to handle the execution of this function when called by Gemini, mapping the name to your Python code that interacts with ERPNext.

## Contributing

Contributions are welcome! Please follow these steps:

1.  Fork the repository.
2.  Create a new branch for your feature or bug fix (`git checkout -b feature/your-feature-name`).
3.  Make your changes.
4.  Commit your changes (`git commit -am 'Add some feature'`).
5.  Push to the branch (`git push origin feature/your-feature-name`).
6.  Create a new Pull Request.

Please ensure your code adheres to existing style conventions and includes relevant tests where applicable.

## License

This project is licensed under the MIT License - see the [LICENSE.txt](license.txt) file for details.
