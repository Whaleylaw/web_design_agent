# Persistence in WordPress Memory Agent

The agent now supports full persistence of both conversation history and long-term memories between sessions.

## How Persistence Works

When you run `python main.py sqlite`, the agent uses two persistence mechanisms:

1. **SQLite Database (`memory_agent.db`)** - Stores conversation history and agent state
2. **JSON File (`memories.json`)** - Stores long-term memories extracted from conversations

### Key Differences

| Feature | In-Memory (Default) | SQLite Persistence |
|---------|-------------------|-------------------|
| **Data Storage** | RAM only | Database file on disk |
| **Persistence** | Lost when program exits | Saved between sessions |
| **Conversation History** | Current session only | All sessions preserved |
| **Thread Management** | Session-based | Can resume previous threads |
| **Performance** | Fastest | Slightly slower (disk I/O) |
| **Use Case** | Quick interactions | Long-term conversations |

## How It Works

### 1. In-Memory Storage (Default)
```python
# When you run: python main.py
checkpointer = MemorySaver()  # Data stored in RAM
```
- Conversations are stored temporarily in memory
- When you exit the program, all conversation history is lost
- Each new session starts fresh
- Best for testing and one-off interactions

### 2. SQLite Persistence
```python
# When you run: python main.py sqlite
checkpointer = SqliteSaver.from_conn_string("memory_agent.db")
```
- Conversations are saved to `memory_agent.db` file
- History persists between program runs
- Can resume previous conversations using thread IDs
- Best for production use and ongoing interactions

## Benefits of SQLite Persistence

1. **Conversation Continuity**
   - Resume conversations days or weeks later
   - Agent remembers context from previous sessions
   - No need to re-explain your situation

2. **History Tracking**
   - Review past conversations
   - Audit trail of all interactions
   - Analytics on usage patterns

3. **Multi-Session Support**
   - Different thread IDs for different conversations
   - Separate contexts for different topics
   - User-specific conversation threads

4. **Reliability**
   - Survives program crashes
   - Can backup conversation data
   - Portable database file

## Example Usage

### First Session (with SQLite)
```bash
$ python main.py sqlite
✅ Using SQLite persistence

You: My name is John and I work at Acme Corp
Assistant: Nice to meet you, John! I'll remember that you work at Acme Corp.

You: quit
👋 Goodbye!
```

### Second Session (days later)
```bash
$ python main.py sqlite
✅ Using SQLite persistence

You: Do you remember where I work?
Assistant: Yes, you work at Acme Corp, John!
```

## Database Structure

The SQLite database (`memory_agent.db`) stores:
- **Checkpoints**: Conversation states at different points
- **Messages**: Full conversation history
- **Thread Metadata**: Information about conversation threads
- **User Context**: Per-user conversation separation

## Important Notes

1. **Long-term Memory vs SQLite Persistence**
   - SQLite stores conversation *history* (what was said)
   - Long-term memory stores *facts* (what to remember)
   - They work together but serve different purposes

2. **Database Location**
   - File created in project directory: `memory_agent.db`
   - Can be backed up or moved to another system
   - Delete the file to start fresh

3. **Thread Management**
   - Default thread_id: "memory_conversation"
   - Can be customized for different conversation contexts
   - Same thread_id resumes previous conversation

## When to Use Each Mode

### Use In-Memory When:
- Testing or developing
- Quick one-off questions
- Privacy is paramount (no disk storage)
- Maximum performance needed

### Use SQLite When:
- Production deployment
- Ongoing conversations
- Need conversation history
- Multiple users/contexts
- Want to analyze past interactions

## Technical Implementation

The choice between in-memory and SQLite is made at runtime:

```python
def create_memory_agent_system(use_sqlite: bool = False):
    if use_sqlite:
        checkpointer = SqliteSaver.from_conn_string("memory_agent.db")
        print("✅ Using SQLite persistence")
    else:
        checkpointer = MemorySaver()
        print("✅ Using in-memory persistence")
```

Both use the same LangGraph checkpoint interface, making them interchangeable.