# WordPress Memory Agent

A LangGraph agent that combines sophisticated memory capabilities with WordPress API integration, allowing you to manage WordPress sites while maintaining context across conversations. Now includes a comprehensive Streamlit UI for an enhanced user experience!

## Features

- 🧠 **Dual Memory System** - Short-term conversation memory + long-term semantic storage
- 🌐 **WordPress Integration** - Access and manage WordPress content via REST API
- 🔍 **Semantic Search** - Find relevant memories using vector similarity
- 💾 **Persistent Storage** - Choose between in-memory or SQLite persistence
- 🛠️ **Tool-Based Architecture** - Explicit control over memory and WordPress operations
- 👤 **User-Specific Memory** - Separate memory spaces for different users
- 🔐 **Secure Authentication** - WordPress API access with application passwords
- 🎨 **Streamlit UI** - Modern web interface with chat, dashboard, and content management

## Quick Start

### 1. Setup

```bash
# Clone and navigate to the project
cd wordpress_agent

# Create and activate virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Setup environment variables
cp .env_example .env
# Edit .env with your OpenAI API key
```

### 2. Configure WordPress

Edit `wp-sites.json` with your WordPress site credentials:
```json
{
    "lawyerinc": {
        "URL": "https://your-site.com/",
        "USER": "your_username",
        "PASS": "your_app_password"
    }
}
```

### 3. Run the Agent

#### Command Line Interface
```bash
# Default: Run with in-memory persistence
python main.py

# Run with SQLite persistence (saves conversations)
python main.py sqlite

# View example interactions
python main.py example
```

#### Streamlit Web Interface

**Option 1: Management Dashboard (streamlit_app.py)**
```bash
# Run the management-focused UI
streamlit run streamlit_app.py
```
This interface provides WordPress management tools with a persistent chat sidebar.

**Option 2: Visual Editor - Basic (streamlit_app_v2.py)**
```bash
# Run the basic visual editor
streamlit run streamlit_app_v2.py
```

**Option 3: Enhanced Visual Editor (streamlit_visual_editor_enhanced.py) - Recommended**
```bash
# Run the enhanced visual editor with Coming Soon mode handling
streamlit run streamlit_visual_editor_enhanced.py
```

The Enhanced Visual Editor provides a revolutionary way to edit your WordPress site:

**🎨 Smart Preview Modes**
- **Live Preview** - See your actual WordPress site in an iframe
- **Content View** - Direct content display (useful for Coming Soon sites)
- Automatic detection of Coming Soon mode
- Seamless switching between preview modes

**🤖 Natural Language Editing**
- Simply describe what you want to change
- "Change the background color to blue"
- "Add a contact form to this page"
- "Update the heading to say 'Welcome to Our Services'"
- "Add a new section with three columns"

**✨ Visual Editing Capabilities**
- **CSS Changes** - Colors, fonts, spacing, backgrounds
- **Content Updates** - Edit text, headings, and paragraphs
- **Add Elements** - Insert new sections, buttons, forms
- **Structure Analysis** - AI understands your page layout

**🚀 Enhanced Features**
- **Natural Language Navigation** - "Show me the Color Test page"
- **Blank Page Creation** - "Create a new blank page"
- **Page Linking** - "Add this page to the main menu"
- **Coming Soon Handling** - Works even when site is not public
- **Quick Actions** - One-click common tasks

**🔄 Iterative Workflow**
1. Navigate to any page using dropdown or natural language
2. Tell the AI what you want to change
3. See changes in real-time (Content View) or after refresh (Live View)
4. Continue refining until perfect

**Example Commands:**
- "Change the hero section background to gradient blue"
- "Add a testimonials section after the services"
- "Make the font size larger in the main content"
- "Replace the contact information with our new address"
- "Add a call-to-action button that says 'Get Started'"

All editing happens through natural conversation with the AI assistant!

## Available Tools

### Memory Tools
- **remember_info** - Store important information for future reference
- **search_memory** - Find relevant information from past conversations
- **list_all_memories** - Show all stored memories

### WordPress Tools

#### Content Management
- **wp_create_post** - Create new posts (draft or publish)
- **wp_update_post** - Update existing posts
- **wp_delete_post** - Delete posts (trash or permanent)
- **wp_get_posts** - Retrieve posts with filtering
- **wp_create_page** - Create new pages
- **wp_update_page** - Update existing pages
- **wp_get_pages** - Retrieve pages

#### Media Management
- **wp_get_media** - Browse media library
- **wp_update_media_metadata** - Update media titles, captions, alt text

#### Taxonomy Management
- **wp_get_categories** - List all categories
- **wp_create_category** - Create new categories
- **wp_get_tags** - List all tags
- **wp_create_tag** - Create new tags

#### Site Management
- **wp_get_site_info** - Get comprehensive site information
- **wp_update_site_settings** - Update site title, tagline, timezone
- **wp_get_themes** - List available themes
- **wp_get_plugins** - List installed plugins
- **wp_get_menus** - Get navigation menus
- **wp_get_menu_items** - Get menu items

#### User & Comment Management
- **wp_get_users** - List WordPress users
- **wp_get_current_user** - Get authenticated user info
- **wp_get_comments** - Retrieve comments
- **wp_moderate_comment** - Approve/spam/trash comments

#### Advanced Features
- **wp_get_blocks** - Get reusable blocks
- **wp_create_block** - Create reusable blocks
- **wp_search** - Search across all content
- **wp_api_request** - Make custom API requests

#### Visual Editing Tools (New!)
- **wp_add_custom_css_to_page** - Add CSS styles to any page
- **wp_add_content_block_to_page** - Insert HTML content blocks
- **wp_get_page_structure** - Analyze page layout and structure
- **wp_update_page_section** - Update specific text sections

## Usage Examples

### Memory Operations
```
You: Remember that this site is for a law firm called Lawyer Incorporated
Assistant: I've remembered that the site is for a law firm called Lawyer Incorporated.

You: What do you remember about the WordPress site?
Assistant: I remember that the site is for a law firm called Lawyer Incorporated.
```

### WordPress Operations
```
You: Show me the latest posts from my WordPress site
Assistant: Here are the latest posts from "Lawyer Incorporated":
1. Updated Hello World - May 13, 2025

You: How many pages does the site have?
Assistant: The site "Lawyer Incorporated" currently has 2 published pages:
1. LawyersInc – Find the Right Attorney
2. About
```

### Visual Editing Operations (New!)
```
You: [Viewing page ID 6] Change the background color to light blue
Assistant: I'll add custom CSS to change the background color to light blue.
[Updates page with CSS]
Successfully added CSS to page 6. The background is now light blue.

You: Add a contact section with our phone number
Assistant: I'll add a new contact section to the page.
[Adds HTML content block]
Successfully added a contact section with your phone number.

You: Update the heading to say "Find Your Perfect Legal Representative"
Assistant: I'll update the heading text for you.
[Updates specific text]
Successfully updated the heading. The page now displays "Find Your Perfect Legal Representative".
```

## Configuration

### Environment Variables (.env)
```
OPENAI_API_KEY=your_openai_api_key_here
```

### WordPress Credentials (wp-sites.json)
Store your WordPress site credentials with application passwords for secure API access.

## Technical Details

- Built with LangGraph 0.4.5 and LangChain 0.3.x
- Uses OpenAI GPT-4o-mini model by default
- Supports both in-memory and SQLite persistence
- Implements WordPress REST API v2
- Streamlit UI with persistent chat sidebar for seamless workflow
- Two-column layout: main content (2/3) and chat (1/3)
- Real-time interaction between agent and WordPress content

## Extending the Agent

The agent can be extended to support more WordPress endpoints listed in `wp_endpoint.txt`, including:
- Creating and updating posts/pages
- Managing media uploads
- Handling comments
- Theme and plugin management
- And much more!

## Security Notes

- Never commit your `.env` file or `wp-sites.json` with real credentials
- Use WordPress application passwords instead of your main password
- The agent uses HTTPS and basic authentication for API requests

## Troubleshooting

### Common Issues

**Streamlit not starting:**
- Ensure virtual environment is activated: `source venv/bin/activate`
- Verify all dependencies installed: `pip install -r requirements.txt`
- Check OpenAI API key is set in `.env` file

**WordPress API connection errors:**
- Verify credentials in `wp-sites.json` are correct
- Ensure WordPress site has REST API enabled
- Check that application passwords are enabled on your WordPress site

**Token limit errors:**
- The agent uses a concise system prompt to minimize token usage
- Consider using `gpt-4o-mini` for cost-effective operation
- The WordPress tools return limited results by default (5 items)

### Persistence Options

- **In-memory mode** (default): Conversations and memories last only for the current session
- **SQLite mode** (`python main.py sqlite` or Streamlit UI): 
  - Conversation history saved to `memory_agent.db`
  - Long-term memories saved to `memories.json`
  - Both persist between sessions

## Development

Built with the latest versions:
- Streamlit 1.41.1
- LangGraph 0.4.5
- LangChain 0.3.x
- All components use Context7-verified best practices

## Contributing

Contributions are welcome! Please ensure you:
1. Follow the existing code style
2. Test with both CLI and Streamlit interfaces
3. Update documentation as needed

## License

MIT License - see LICENSE file for details