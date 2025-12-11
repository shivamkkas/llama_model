"""
Example usage scripts for MCP Server
Demonstrates all major features
"""
import requests
import json
import asyncio
import websockets

BASE_URL = "http://localhost:8000"


class MCPClient:
    """Simple client for interacting with MCP Server"""
    
    def __init__(self, base_url: str = BASE_URL):
        self.base_url = base_url
        self.session = requests.Session()
    
    def health_check(self):
        """Check server health"""
        response = self.session.get(f"{self.base_url}/health")
        return response.json()
    
    def query(self, message: str, user_id: str = "user_1", conversation_id: str = None):
        """Send a query to the server"""
        payload = {
            "message": message,
            "user_id": user_id
        }
        if conversation_id:
            payload["conversation_id"] = conversation_id
        
        response = self.session.post(
            f"{self.base_url}/query",
            json=payload
        )
        return response.json()
    
    def upload_document(self, content: str, filename: str, user_id: str = "user_1"):
        """Upload a document"""
        payload = {
            "file_content": content,
            "filename": filename,
            "user_id": user_id
        }
        response = self.session.post(
            f"{self.base_url}/documents/upload",
            json=payload
        )
        return response.json()
    
    def search_documents(self, query: str, user_id: str = "user_1", top_k: int = 5):
        """Search documents"""
        payload = {
            "query": query,
            "user_id": user_id,
            "top_k": top_k
        }
        response = self.session.post(
            f"{self.base_url}/documents/search",
            json=payload
        )
        return response.json()
    
    def register_api(self, name: str, base_url: str, description: str, endpoints: list):
        """Register an external API"""
        payload = {
            "name": name,
            "base_url": base_url,
            "description": description,
            "endpoints": endpoints
        }
        response = self.session.post(
            f"{self.base_url}/api/register",
            json=payload
        )
        return response.json()
    
    def get_conversation(self, conversation_id: str):
        """Get conversation history"""
        response = self.session.get(
            f"{self.base_url}/conversations/{conversation_id}"
        )
        return response.json()


def example_1_database_query():
    """Example 1: Query database tables"""
    print("\n" + "="*60)
    print("Example 1: Database Query")
    print("="*60)
    
    client = MCPClient()
    
    # Simple query
    print("\n1. Simple database query:")
    result = client.query(
        message="Show me all customers in the database",
        user_id="user_1"
    )
    print(f"Response: {result['response'][:200]}...")
    print(f"Sources: {result['sources']}")
    
    # Complex query with conditions
    print("\n2. Complex query with filtering:")
    result = client.query(
        message="Find all transactions over $100 in the last month",
        user_id="user_1"
    )
    print(f"Response: {result['response'][:200]}...")
    
    # Aggregation query
    print("\n3. Aggregation query:")
    result = client.query(
        message="What is the total revenue by customer?",
        user_id="user_1"
    )
    print(f"Response: {result['response'][:200]}...")


def example_2_document_management():
    """Example 2: Upload and search documents"""
    print("\n" + "="*60)
    print("Example 2: Document Management")
    print("="*60)
    
    client = MCPClient()
    
    # Upload documents
    print("\n1. Uploading documents...")
    
    doc1_content = """
    Machine Learning Best Practices
    
    1. Data Preprocessing: Always clean and normalize your data
    2. Feature Engineering: Create meaningful features from raw data
    3. Model Selection: Choose the right algorithm for your problem
    4. Hyperparameter Tuning: Optimize model parameters
    5. Cross-Validation: Validate model performance properly
    """
    
    doc2_content = """
    Deep Learning Tutorial
    
    Neural networks are composed of layers:
    - Input Layer: Receives the data
    - Hidden Layers: Process the information
    - Output Layer: Produces the final result
    
    Common architectures include CNNs for images and RNNs for sequences.
    """
    
    result1 = client.upload_document(doc1_content, "ml_guide.txt", "user_1")
    print(f"Uploaded: {result1}")
    
    result2 = client.upload_document(doc2_content, "dl_tutorial.txt", "user_1")
    print(f"Uploaded: {result2}")
    
    # Search documents
    print("\n2. Searching documents:")
    search_result = client.search_documents(
        query="How do I prepare data for machine learning?",
        user_id="user_1"
    )
    print(f"Found {len(search_result['results'])} results")
    for i, result in enumerate(search_result['results'][:2], 1):
        print(f"\nResult {i}:")
        print(f"  Content: {result['content'][:100]}...")
        print(f"  Score: {result['score']}")
    
    # Query with document context
    print("\n3. Query using documents:")
    result = client.query(
        message="What are the best practices for machine learning?",
        user_id="user_1"
    )
    print(f"Response: {result['response'][:200]}...")


def example_3_external_api():
    """Example 3: Register and use external APIs"""
    print("\n" + "="*60)
    print("Example 3: External API Integration")
    print("="*60)
    
    client = MCPClient()
    
    # Register a mock weather API
    print("\n1. Registering external API...")
    result = client.register_api(
        name="weather_api",
        base_url="https://api.openweathermap.org/data/2.5",
        description="Weather information API",
        endpoints=[
            {
                "path": "weather",
                "method": "GET",
                "description": "Get current weather for a location"
            }
        ]
    )
    print(f"API registered: {result}")
    
    # Query using the API
    print("\n2. Querying through registered API:")
    result = client.query(
        message="What's the weather like in San Francisco?",
        user_id="user_1"
    )
    print(f"Response: {result['response'][:200]}...")


def example_4_conversation_history():
    """Example 4: Multi-turn conversation"""
    print("\n" + "="*60)
    print("Example 4: Conversation History")
    print("="*60)
    
    client = MCPClient()
    
    # First message
    print("\n1. Starting conversation:")
    result1 = client.query(
        message="Tell me about the customers in our database",
        user_id="user_1"
    )
    print(f"Response: {result1['response'][:150]}...")
    conversation_id = result1['conversation_id']
    print(f"Conversation ID: {conversation_id}")
    
    # Follow-up message (maintains context)
    print("\n2. Follow-up question:")
    result2 = client.query(
        message="Which one has the highest transaction value?",
        user_id="user_1",
        conversation_id=conversation_id
    )
    print(f"Response: {result2['response'][:150]}...")
    
    # Another follow-up
    print("\n3. Another follow-up:")
    result3 = client.query(
        message="Show me their contact information",
        user_id="user_1",
        conversation_id=conversation_id
    )
    print(f"Response: {result3['response'][:150]}...")
    
    # Retrieve full conversation
    print("\n4. Retrieving full conversation history:")
    history = client.get_conversation(conversation_id)
    print(f"Total messages: {len(history['history'])}")
    for msg in history['history']:
        print(f"  [{msg['role']}]: {msg['content'][:80]}...")


def example_5_complex_multi_step():
    """Example 5: Complex multi-step query"""
    print("\n" + "="*60)
    print("Example 5: Complex Multi-Step Query")
    print("="*60)
    
    client = MCPClient()
    
    # Upload some reference documents first
    print("\n1. Setting up reference documents...")
    
    policy_doc = """
    Company Refund Policy
    
    - Full refund available within 30 days
    - Partial refund (50%) available within 60 days
    - No refund after 90 days
    - Processing time: 5-7 business days
    """
    
    client.upload_document(policy_doc, "refund_policy.txt", "user_1")
    
    # Complex query that requires multiple steps
    print("\n2. Executing complex query:")
    result = client.query(
        message="""
        Find all customers who made purchases in the last 45 days,
        then check our refund policy to see if they're eligible for refunds,
        and summarize the results.
        """,
        user_id="user_1"
    )
    
    print(f"\nResponse: {result['response']}")
    print(f"\nSources used:")
    for source in result['sources']:
        print(f"  - {source['type']}: {source}")
    print(f"\nMetadata: {result['metadata']}")


async def example_6_websocket_streaming():
    """Example 6: Real-time streaming via WebSocket"""
    print("\n" + "="*60)
    print("Example 6: WebSocket Streaming")
    print("="*60)
    
    uri = "ws://localhost:8000/ws"
    
    try:
        async with websockets.connect(uri) as websocket:
            # Send query
            query = {
                "message": "Tell me about all the transactions in the database",
                "user_id": "user_1"
            }
            
            print(f"\nSending query: {query['message']}")
            await websocket.send(json.dumps(query))
            
            # Receive streaming response
            print("\nStreaming response:")
            response = await websocket.recv()
            data = json.loads(response)
            print(f"Received: {data}")
    
    except Exception as e:
        print(f"WebSocket error (server might not be running): {e}")


def run_all_examples():
    """Run all examples"""
    client = MCPClient()
    
    # Check if server is running
    try:
        health = client.health_check()
        print("Server Health Check:")
        print(json.dumps(health, indent=2))
    except Exception as e:
        print(f"Error: Cannot connect to server at {BASE_URL}")
        print(f"Make sure the server is running with: docker-compose up")
        return
    
    # Run examples
    example_1_database_query()
    example_2_document_management()
    example_3_external_api()
    example_4_conversation_history()
    example_5_complex_multi_step()
    
    # WebSocket example (requires async)
    print("\n\nRunning WebSocket example...")
    try:
        asyncio.run(example_6_websocket_streaming())
    except Exception as e:
        print(f"Skipping WebSocket example: {e}")
    
    print("\n" + "="*60)
    print("All examples completed!")
    print("="*60)


if __name__ == "__main__":
    run_all_examples()