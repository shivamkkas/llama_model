"""
Agent Orchestrator using LangGraph for decision-making
Routes queries to appropriate handlers based on intent
"""
from typing import Dict, Any, List, Optional, AsyncIterator, TypedDict
from dataclasses import dataclass, asdict
from enum import Enum
import json
import re
from datetime import datetime

from langgraph.graph import StateGraph, END
from langchain_community.llms import Ollama
from langchain.prompts import PromptTemplate
from langchain.schema import BaseMessage, HumanMessage, AIMessage, SystemMessage

from config.config import Config
from app.db.manager import DatabaseManager
from app.documents.docs_manager import DocumentManager
from app.apis.external import APIManager
from app.conversation.conversation_manager import ConversationManager


class IntentType(str, Enum):
    DATABASE_QUERY = "database_query"
    DOCUMENT_SEARCH = "document_search"
    API_CALL = "api_call"
    GENERAL_CHAT = "general_chat"
    MULTI_STEP = "multi_step"


# Use TypedDict instead of dataclass for LangGraph state
class AgentState(TypedDict, total=False):
    """State object passed through the graph"""
    user_message: str
    conversation_id: Optional[str]
    user_id: str
    context: Dict[str, Any]
    
    # Intent classification
    intent: Optional[str]
    confidence: float
    
    # Extracted information
    database_query: Optional[str]
    target_database: Optional[str]
    search_query: Optional[str]
    api_name: Optional[str]
    api_params: Optional[Dict[str, Any]]
    
    # Results
    database_results: Optional[List[Dict]]
    document_results: Optional[List[Dict]]
    api_results: Optional[Dict[str, Any]]
    
    # Final response
    response: str
    metadata: Dict[str, Any]
    sources: List[Dict[str, Any]]
    
    # Error handling
    errors: List[str]


class AgentOrchestrator:
    def __init__(
        self,
        config: Config,
        db_manager: DatabaseManager,
        doc_manager: DocumentManager,
        api_manager: APIManager,
        conv_manager: ConversationManager
    ):
        self.config = config
        self.db_manager = db_manager
        self.doc_manager = doc_manager
        self.api_manager = api_manager
        self.conv_manager = conv_manager
        
        # Initialize Ollama LLM
        self.llm = Ollama(
            base_url=config.ollama.host,
            model=config.ollama.model,
            temperature=config.ollama.temperature,
        )
        
        # Build the LangGraph workflow
        self.graph = self._build_graph()
    
    def _build_graph(self) -> StateGraph:
        """Build the LangGraph decision workflow"""
        workflow = StateGraph(AgentState)
        
        # Add nodes
        workflow.add_node("classify_intent", self._classify_intent)
        workflow.add_node("route_query", self._route_query)
        workflow.add_node("handle_database", self._handle_database)
        workflow.add_node("handle_documents", self._handle_documents)
        workflow.add_node("handle_api", self._handle_api)
        workflow.add_node("handle_general", self._handle_general)
        workflow.add_node("handle_multi_step", self._handle_multi_step)
        workflow.add_node("generate_response", self._generate_response)
        
        # Set entry point
        workflow.set_entry_point("classify_intent")
        
        # Add edges
        workflow.add_edge("classify_intent", "route_query")
        
        # Conditional routing based on intent
        workflow.add_conditional_edges(
            "route_query",
            self._routing_decision,
            {
                IntentType.DATABASE_QUERY.value: "handle_database",
                IntentType.DOCUMENT_SEARCH.value: "handle_documents",
                IntentType.API_CALL.value: "handle_api",
                IntentType.GENERAL_CHAT.value: "handle_general",
                IntentType.MULTI_STEP.value: "handle_multi_step",
            }
        )
        
        # All handlers lead to response generation
        workflow.add_edge("handle_database", "generate_response")
        workflow.add_edge("handle_documents", "generate_response")
        workflow.add_edge("handle_api", "generate_response")
        workflow.add_edge("handle_general", "generate_response")
        workflow.add_edge("handle_multi_step", "generate_response")
        workflow.add_edge("generate_response", END)
        
        return workflow.compile()
    
    async def _classify_intent(self, state: AgentState) -> Dict[str, Any]:
        """Classify the user's intent using Ollama"""
        
        classification_prompt = f"""Analyze the following user message and classify its intent.

User Message: {state['user_message']}

Available intents:
1. DATABASE_QUERY - User wants to query a database table
2. DOCUMENT_SEARCH - User wants to search through uploaded documents
3. API_CALL - User wants to fetch data from an external API
4. GENERAL_CHAT - General conversation or question
5. MULTI_STEP - Requires multiple operations (database + documents, etc.)

Respond ONLY with a JSON object in this format:
{{
    "intent": "intent_name",
    "confidence": 0.95,
    "reasoning": "brief explanation"
}}"""
        
        try:
            response = await self.llm.ainvoke(classification_prompt)
            
            # Parse JSON from response
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                result = json.loads(json_match.group())
                intent_value = result["intent"].lower()
                
                # Validate intent
                try:
                    IntentType(intent_value)
                except ValueError:
                    intent_value = IntentType.GENERAL_CHAT.value
                
                metadata = state.get('metadata', {})
                metadata["classification_reasoning"] = result.get("reasoning", "")
                
                return {
                    "intent": intent_value,
                    "confidence": result["confidence"],
                    "metadata": metadata
                }
        
        except Exception as e:
            errors = state.get('errors', [])
            errors.append(f"Classification error: {str(e)}")
            return {
                "intent": IntentType.GENERAL_CHAT.value,
                "confidence": 0.5,
                "errors": errors
            }
    
    def _routing_decision(self, state: AgentState) -> str:
        """Decide which handler to route to"""
        return state.get('intent', IntentType.GENERAL_CHAT.value)
    
    async def _route_query(self, state: AgentState) -> Dict[str, Any]:
        """Extract specific information based on intent"""
        
        intent = state.get('intent')
        
        if intent == IntentType.DATABASE_QUERY.value:
            return await self._extract_database_info(state)
        
        elif intent == IntentType.DOCUMENT_SEARCH.value:
            return await self._extract_search_info(state)
        
        elif intent == IntentType.API_CALL.value:
            return await self._extract_api_info(state)
        
        return {}
    
    async def _extract_database_info(self, state: AgentState) -> Dict[str, Any]:
        """Extract database name and generate SQL query"""
        
        available_dbs = list(self.config.databases.keys())
        available_tables = await self.db_manager.get_accessible_tables(state['user_id'])
        
        extraction_prompt = f"""Generate a SQL query for the following request.

User Request: {state['user_message']}

Available Databases: {', '.join(available_dbs)}
Accessible Tables: {', '.join(available_tables)}

Respond ONLY with a JSON object:
{{
    "database": "database_name",
    "query": "SELECT * FROM table WHERE ...",
    "explanation": "what the query does"
}}"""
        
        try:
            response = await self.llm.ainvoke(extraction_prompt)
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                result = json.loads(json_match.group())
                metadata = state.get('metadata', {})
                metadata["query_explanation"] = result["explanation"]
                
                return {
                    "target_database": result["database"],
                    "database_query": result["query"],
                    "metadata": metadata
                }
        
        except Exception as e:
            errors = state.get('errors', [])
            errors.append(f"Database extraction error: {str(e)}")
            return {"errors": errors}
        
        return {}
    
    async def _extract_search_info(self, state: AgentState) -> Dict[str, Any]:
        """Extract document search query"""
        return {"search_query": state['user_message']}
    
    async def _extract_api_info(self, state: AgentState) -> Dict[str, Any]:
        """Extract API name and parameters"""
        
        available_apis = await self.api_manager.list_apis()
        
        extraction_prompt = f"""Extract API call information from the user request.

User Request: {state['user_message']}

Available APIs: {json.dumps(available_apis, indent=2)}

Respond ONLY with a JSON object:
{{
    "api_name": "api_name",
    "parameters": {{"param1": "value1"}},
    "endpoint": "endpoint_path"
}}"""
        
        try:
            response = await self.llm.ainvoke(extraction_prompt)
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                result = json.loads(json_match.group())
                metadata = state.get('metadata', {})
                metadata["api_endpoint"] = result.get("endpoint", "")
                
                return {
                    "api_name": result["api_name"],
                    "api_params": result["parameters"],
                    "metadata": metadata
                }
        
        except Exception as e:
            errors = state.get('errors', [])
            errors.append(f"API extraction error: {str(e)}")
            return {"errors": errors}
        
        return {}
    async def _handle_database(self, state: AgentState) -> Dict[str, Any]:
        """Execute database query"""
        try:
            database_query = state.get('database_query')
            target_database = state.get('target_database')
            
            if database_query and target_database:
                results = await self.db_manager.execute_query(
                    query=database_query,
                    database=target_database,
                    user_id=state['user_id']
                )
                
                sources = state.get('sources', [])
                sources.append({
                    "type": "database",
                    "database": target_database,
                    "query": database_query
                })
                
                return {
                    "database_results": results,
                    "sources": sources
                }
        except Exception as e:
            errors = state.get('errors', [])
            errors.append(f"Database execution error: {str(e)}")
            return {"errors": errors}
        
        return {}
    
    async def _handle_documents(self, state: AgentState) -> Dict[str, Any]:
        """Search documents"""
        try:
            search_query = state.get('search_query')
            if search_query:
                results = await self.doc_manager.search_documents(
                    query=search_query,
                    user_id=state['user_id'],
                    top_k=5
                )
                
                sources = state.get('sources', [])
                sources.extend([
                    {"type": "document", "id": doc["id"], "score": doc["score"]}
                    for doc in results
                ])
                
                return {
                    "document_results": results,
                    "sources": sources
                }
        except Exception as e:
            errors = state.get('errors', [])
            errors.append(f"Document search error: {str(e)}")
            return {"errors": errors}
        
        return {}
    
    async def _handle_api(self, state: AgentState) -> Dict[str, Any]:
        """Call external API"""
        try:
            api_name = state.get('api_name')
            api_params = state.get('api_params')
            
            if api_name and api_params:
                results = await self.api_manager.call_api(
                    api_name=api_name,
                    params=api_params
                )
                
                sources = state.get('sources', [])
                sources.append({
                    "type": "api",
                    "api_name": api_name,
                    "params": api_params
                })
                
                return {
                    "api_results": results,
                    "sources": sources
                }
        except Exception as e:
            errors = state.get('errors', [])
            errors.append(f"API call error: {str(e)}")
            return {"errors": errors}
        
        return {}
    
    async def _handle_general(self, state: AgentState) -> Dict[str, Any]:
        """Handle general conversation"""
        # Just pass through - response will be generated in next step
        return {}
    
    async def _handle_multi_step(self, state: AgentState) -> Dict[str, Any]:
        """Handle queries requiring multiple operations"""
        # This could recursively call other handlers
        # For now, simplified implementation
        return {}
    
    async def _generate_response(self, state: AgentState) -> Dict[str, Any]:
        """Generate final response based on gathered information"""
        
        # Gather conversation history
        history = []
        conversation_id = state.get('conversation_id')
        if conversation_id:
            history = await self.conv_manager.get_conversation(conversation_id)
        
        # Build context
        context_parts = []
        
        database_results = state.get('database_results')
        if database_results:
            context_parts.append(f"Database Results:\n{json.dumps(database_results, indent=2)}")
        
        document_results = state.get('document_results')
        if document_results:
            context_parts.append(f"Document Results:\n{json.dumps(document_results, indent=2)}")
        
        api_results = state.get('api_results')
        if api_results:
            context_parts.append(f"API Results:\n{json.dumps(api_results, indent=2)}")
        
        context_str = "\n\n".join(context_parts) if context_parts else "No additional context"
        
        # Generate response
        response_prompt = f"""Based on the user's question and the available information, provide a helpful response.

User Question: {state['user_message']}

Context:
{context_str}

Conversation History:
{json.dumps(history[-5:], indent=2) if history else "No previous messages"}

Provide a clear, concise, and helpful response."""
        
        try:
            response = await self.llm.ainvoke(response_prompt)
            
            # Save to conversation history
            if conversation_id:
                await self.conv_manager.add_message(
                    conversation_id=conversation_id,
                    role="user",
                    content=state['user_message']
                )
                await self.conv_manager.add_message(
                    conversation_id=conversation_id,
                    role="assistant",
                    content=response,
                    metadata=state.get('metadata', {})
                )
            else:
                # Create new conversation
                conversation_id = await self.conv_manager.create_conversation(
                    user_id=state['user_id'],
                    initial_message=state['user_message'],
                    response=response
                )
            
            return {
                "response": response,
                "conversation_id": conversation_id
            }
        
        except Exception as e:
            errors = state.get('errors', [])
            errors.append(f"Response generation error: {str(e)}")
            return {
                "response": "I apologize, but I encountered an error generating a response.",
                "errors": errors
            }
    
    async def process_query(
        self,
        message: str,
        conversation_id: Optional[str],
        user_id: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Process a user query through the agent graph"""
        
        # Create initial state as a dictionary
        initial_state: AgentState = {
            "user_message": message,
            "conversation_id": conversation_id,
            "user_id": user_id,
            "context": context or {},
            "intent": None,
            "confidence": 0.0,
            "database_query": None,
            "target_database": None,
            "search_query": None,
            "api_name": None,
            "api_params": None,
            "database_results": None,
            "document_results": None,
            "api_results": None,
            "response": "",
            "metadata": {},
            "sources": [],
            "errors": []
        }
        
        # Run through the graph
        final_state = await self.graph.ainvoke(initial_state)
        
        return {
            "response": final_state.get("response", ""),
            "conversation_id": final_state.get("conversation_id"),
            "metadata": final_state.get("metadata", {}),
            "sources": final_state.get("sources", [])
        }
    
    async def stream_query(
        self,
        message: str,
        conversation_id: Optional[str],
        user_id: str
    ) -> AsyncIterator[Dict[str, Any]]:
        """Stream the query processing (simplified version)"""
        # This would require streaming implementation through the graph
        # For now, return the full response
        result = await self.process_query(message, conversation_id, user_id)
        yield result
    
    async def check_ollama_health(self) -> bool:
        """Check if Ollama is accessible"""
        try:
            await self.llm.ainvoke("test")
            return True
        except:
            return False
    
    async def initialize(self):
        """Initialize the orchestrator"""
        pass
    
    async def cleanup(self):
        """Cleanup resources"""
        pass