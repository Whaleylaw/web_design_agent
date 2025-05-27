# WordPress Agent UI - Streamlit Implementation

## Project Overview

Create a Streamlit-based user interface for a WordPress site management agent built with LangGraph. The UI will provide an intuitive chat interface combined with a WordPress dashboard for managing content, media, and site settings through AI conversation.

## Current Setup

- **Existing Agent**: LangGraph-based WordPress management agent
- **WordPress Site**: LawyerIncorporated.com (https://lawyerincorporated.com/)
- **API Access**: Full WordPress REST API access via WordPress MCP server
- **Available Endpoints**: Comprehensive WordPress API endpoints (see wp_endpoint.txt reference)

## Technical Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Streamlit UI  │────│  LangGraph Agent │────│ WordPress API   │
│                 │    │                  │    │                 │
│ - Chat Interface│    │ - Agent Logic    │    │ - REST Endpoints│
│ - Dashboard     │    │ - Tool Calls     │    │ - Authentication│
│ - File Uploads  │    │ - State Mgmt     │    │ - CRUD Ops      │
└─────────────────┘    └──────────────────┘    └─────────────────┘
```

## Project Structure

```
wordpress-agent-ui/
├── app.py                 # Main Streamlit application
├── requirements.txt       # Python dependencies
├── config/
│   ├── __init__.py
│   ├── settings.py       # App configuration
│   └── wp_config.py      # WordPress site configuration
├── components/
│   ├── __init__.py
│   ├── chat.py           # Chat interface components
│   ├── dashboard.py      # WordPress dashboard
│   ├── content.py        # Content management components
│   ├── media.py          # Media library components
│   └── sidebar.py        # Navigation sidebar
├── services/
│   ├── __init__.py
│   ├── agent_service.py  # LangGraph agent integration
│   ├── wp_service.py     # WordPress API service layer
│   └── utils.py          # Utility functions
├── static/
│   ├── css/
│   │   └── custom.css    # Custom styling
│   └── images/
│       └── logo.png      # App logo/branding
└── README.md
```

## Core Requirements

### 1. Chat Interface
- Real-time conversation with the WordPress agent
- Message history persistence using `st.session_state`
- Support for rich content (markdown, images, links)
- Typing indicators and message status
- Chat input with send button and enter key support
- Message timestamps
- User/assistant message differentiation

### 2. WordPress Dashboard
- **Site Overview Panel**:
  - Total posts, pages, media count
  - Recent activity feed
  - Site health status indicators
  - Quick statistics display

- **Quick Actions Panel**:
  - Create new post/page buttons
  - Upload media shortcut
  - Publish draft content
  - Site backup status

### 3. Content Management
- **Posts/Pages Browser**:
  - Searchable list with filters (published, draft, private)
  - Quick edit capabilities
  - Bulk actions support
  - Preview functionality

- **Media Library**:
  - Grid view of uploaded media
  - Drag-and-drop upload area
  - Image preview and metadata
  - Search and filter capabilities

### 4. Navigation & Layout
- **Sidebar Navigation**:
  - Dashboard home
  - Posts management
  - Pages management  
  - Media library
  - Site settings
  - Chat history

- **Responsive Layout**:
  - Multi-column layout for desktop
  - Collapsible sidebar for mobile
  - Tabbed interface for smaller screens

## Key Features to Implement

### Phase 1: Core Functionality
1. **Basic Chat Interface**
   - Simple message exchange with agent
   - Session state management
   - Basic error handling

2. **WordPress Connection**
   - API authentication setup
   - Basic site information retrieval
   - Connection status indicator

3. **Simple Dashboard**
   - Site statistics display
   - Recent posts/pages list
   - Basic navigation structure

### Phase 2: Enhanced Features
1. **Advanced Chat**
   - Rich message formatting
   - File upload in chat
   - Action confirmations
   - Progress indicators for long operations

2. **Content Management**
   - Visual post/page editor integration
   - Media upload and management
   - Category/tag management
   - Menu management interface

3. **Real-time Updates**
   - Live site statistics
   - Notification system
   - Auto-refresh capabilities

### Phase 3: Advanced Features
1. **AI-Powered Content**
   - Content generation with preview
   - SEO optimization suggestions
   - Image generation integration
   - Automated scheduling

2. **Analytics & Monitoring**
   - Site performance metrics
   - Content engagement tracking
   - Error monitoring and alerts

## Implementation Guidelines

### Streamlit Best Practices
- Use `st.cache_data` for expensive API calls
- Implement proper session state management
- Use `st.rerun()` for dynamic updates
- Handle async operations with progress bars
- Implement proper error boundaries

### Security Considerations
- Secure API key storage
- Input validation and sanitization
- Rate limiting for API calls
- User session management
- HTTPS enforcement

### Performance Optimization
- Lazy loading for large datasets
- Pagination for content lists
- Image optimization for media
- Caching strategies for repeated queries
- Background task processing

## Integration Points

### LangGraph Agent Integration
```python
# Example agent service integration
class AgentService:
    def __init__(self, agent_config):
        self.agent = self.initialize_agent(agent_config)
        
    async def chat_with_agent(self, message: str, context: dict):
        """Send message to LangGraph agent and return response"""
        response = await self.agent.ainvoke({
            "input": message,
            "context": context,
            "session_id": st.session_state.get("session_id")
        })
        return response
```

### WordPress API Integration
```python
# Example WordPress service layer
class WordPressService:
    def __init__(self, site_config):
        self.site_url = site_config["url"]
        self.headers = self.setup_auth(site_config)
        
    async def get_site_stats(self):
        """Retrieve site statistics"""
        # Implementation using WordPress REST API
        pass
        
    async def create_post(self, post_data):
        """Create new WordPress post"""
        # Implementation using WordPress REST API
        pass
```

## UI Components Specifications

### Chat Component
- Left-aligned user messages with blue background
- Right-aligned assistant messages with gray background
- Markdown rendering for rich content
- File attachment support
- Message timestamps
- Typing indicators
- Error message handling

### Dashboard Component
- Card-based layout for statistics
- Color-coded status indicators
- Interactive charts using Plotly
- Responsive grid system
- Quick action buttons
- Real-time data updates

### Content Management Components
- Table-based content listings
- Search and filter bars
- Pagination controls
- Bulk action checkboxes
- Modal dialogs for editing
- Drag-and-drop interfaces

## Styling and Theming

### Custom CSS Requirements
- WordPress admin-inspired color scheme
- Consistent spacing and typography
- Mobile-responsive design
- Dark/light theme toggle
- Professional, clean aesthetic
- Accessibility compliance

### Color Palette
- Primary: #0073aa (WordPress blue)
- Secondary: #005177 (darker blue)
- Success: #46b450 (green)
- Warning: #ffb900 (orange)
- Error: #dc3232 (red)
- Background: #f1f1f1 (light gray)

## Configuration Management

### Environment Variables
```python
# Required environment variables
WORDPRESS_SITE_URL = "https://lawyerincorporated.com"
WORDPRESS_API_USER = "api_user"
WORDPRESS_API_PASSWORD = "application_password"
AGENT_CONFIG_PATH = "path/to/agent/config"
SESSION_SECRET_KEY = "secret_key_for_sessions"
```

### Settings Configuration
```python
# settings.py structure
class Settings:
    WORDPRESS_SITES = {
        "lawyerinc": {
            "url": "https://lawyerincorporated.com",
            "api_user": "api_user",
            "api_password": "app_password"
        }
    }
    
    STREAMLIT_CONFIG = {
        "page_title": "WordPress Agent",
        "page_icon": "🤖",
        "layout": "wide",
        "initial_sidebar_state": "expanded"
    }
```

## Development Phases

### Phase 1: Foundation (Week 1)
- [ ] Set up project structure
- [ ] Implement basic Streamlit app with navigation
- [ ] Create chat interface with session state
- [ ] Integrate with existing LangGraph agent
- [ ] Basic WordPress API connection testing

### Phase 2: Core Features (Week 2)
- [ ] Complete dashboard with site statistics
- [ ] Implement content browsing (posts/pages)
- [ ] Add media library basic functionality
- [ ] Create responsive layout and styling
- [ ] Add error handling and user feedback

### Phase 3: Enhancement (Week 3-4)
- [ ] Advanced chat features (file upload, rich formatting)
- [ ] Content creation and editing capabilities
- [ ] Media upload and management
- [ ] Real-time updates and notifications
- [ ] Performance optimization and caching

## Testing Strategy

### Unit Tests
- Component functionality testing
- API integration testing
- Error handling validation
- Session state management

### Integration Tests
- End-to-end user workflows
- WordPress API interaction testing
- Agent response handling
- Performance benchmarking

### User Acceptance Testing
- Chat interface usability
- Dashboard functionality
- Content management workflows
- Mobile responsiveness

## Deployment Considerations

### Local Development
- Use `streamlit run app.py` for development
- Hot reloading enabled
- Debug mode configuration
- Local environment variables

### Production Deployment
- Streamlit Cloud deployment
- Docker containerization option
- Environment variable management
- SSL/HTTPS configuration
- Performance monitoring

## Success Criteria

1. **Functional Chat Interface**: Users can interact with the WordPress agent naturally through chat
2. **Effective Site Management**: Common WordPress tasks can be completed through the UI
3. **Responsive Design**: Application works well on desktop and mobile devices
4. **Performance**: Fast loading times and responsive interactions
5. **User Experience**: Intuitive navigation and clear feedback mechanisms
6. **Reliability**: Stable operation with proper error handling
7. **Integration**: Seamless communication with existing LangGraph agent

## Next Steps

1. **Setup Development Environment**: Install required dependencies and configure workspace
2. **Create Basic Structure**: Implement the project structure and main application file
3. **Build Core Components**: Start with chat interface and basic dashboard
4. **Integrate Services**: Connect to LangGraph agent and WordPress API
5. **Iterate and Enhance**: Add features progressively based on testing feedback

## Reference Files

- `wp_endpoint.txt`: Complete list of available WordPress API endpoints
- `config/wp-sites.json`: WordPress site configuration (LawyerIncorporated.com)
- Existing LangGraph agent implementation files

## Notes for Implementation

- Prioritize user experience and intuitive design
- Implement comprehensive error handling throughout
- Use Streamlit's built-in components when possible
- Maintain clear separation between UI, business logic, and API layers
- Plan for scalability and future feature additions
- Document all configuration options and setup procedures
