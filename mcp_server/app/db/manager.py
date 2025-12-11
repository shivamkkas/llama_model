"""
Database Manager for SQLite and PostgreSQL
Handles query execution with permission checking
"""
from typing import Dict, List, Optional, Any
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import text, inspect
from sqlalchemy.pool import NullPool
import sqlite3
import asyncpg
from contextlib import asynccontextmanager

from config.config import Config, DatabaseConfig


class DatabaseManager:
    def __init__(self, config: Config):
        self.config = config
        self.engines = {}
        self.session_makers = {}
        self._initialized = False
    
    async def initialize(self):
        """Initialize database connections"""
        if self._initialized:
            return
        
        for db_name, db_config in self.config.databases.items():
            try:
                # Create async engine
                if db_config.type == "sqlite":
                    # Convert to async SQLite URL
                    conn_str = db_config.connection_string.replace(
                        "sqlite:///",
                        "sqlite+aiosqlite:///"
                    )
                elif db_config.type == "postgresql":
                    # Convert to async PostgreSQL URL
                    conn_str = db_config.connection_string.replace(
                        "postgresql://",
                        "postgresql+asyncpg://"
                    )
                else:
                    raise ValueError(f"Unsupported database type: {db_config.type}")
                
                # SQLite doesn't support pooling parameters
                if db_config.type == "sqlite":
                    engine = create_async_engine(
                        conn_str,
                        echo=db_config.echo,
                        poolclass=NullPool
                    )
                else:
                    engine = create_async_engine(
                        conn_str,
                        echo=db_config.echo,
                        pool_size=db_config.pool_size,
                        max_overflow=db_config.max_overflow
                    )
                
                self.engines[db_name] = engine
                self.session_makers[db_name] = async_sessionmaker(
                    engine,
                    class_=AsyncSession,
                    expire_on_commit=False
                )
                
                print(f"✓ Initialized {db_name} database connection")
            
            except Exception as e:
                print(f"✗ Failed to initialize {db_name}: {str(e)}")
        
        self._initialized = True
    
    @asynccontextmanager
    async def get_session(self, database: str):
        """Get a database session"""
        if database not in self.session_makers:
            raise ValueError(f"Database '{database}' not configured")
        
        async with self.session_makers[database]() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise
    
    async def execute_query(
        self,
        query: str,
        database: str,
        user_id: str,
        params: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Execute a query with permission checking"""
        
        # Validate permissions
        if not await self._check_permissions(query, database, user_id):
            raise PermissionError(
                f"User {user_id} does not have permission to access requested tables"
            )
        
        # Validate query safety
        if not self._is_safe_query(query):
            raise ValueError("Query contains potentially dangerous operations")
        
        # Execute query
        async with self.get_session(database) as session:
            result = await session.execute(text(query), params or {})
            
            # Convert to list of dicts
            if result.returns_rows:
                columns = result.keys()
                rows = result.fetchall()
                return [dict(zip(columns, row)) for row in rows]
            else:
                return [{"affected_rows": result.rowcount}]
    
    async def _check_permissions(
        self,
        query: str,
        database: str,
        user_id: str
    ) -> bool:
        """Check if user has permission to access tables in query"""
        
        db_config = self.config.databases.get(database)
        if not db_config:
            return False
        
        # Extract table names from query (simplified)
        tables = self._extract_table_names(query)
        
        # Check permissions
        for table in tables:
            allowed_users = db_config.table_permissions.get(table, [])
            if allowed_users and user_id not in allowed_users:
                return False
        
        return True
    
    def _extract_table_names(self, query: str) -> List[str]:
        """Extract table names from SQL query (simplified)"""
        import re
        
        query_upper = query.upper()
        tables = []
        
        # Match FROM clause
        from_matches = re.findall(r'FROM\s+([a-zA-Z_][a-zA-Z0-9_]*)', query_upper)
        tables.extend(from_matches)
        
        # Match JOIN clauses
        join_matches = re.findall(r'JOIN\s+([a-zA-Z_][a-zA-Z0-9_]*)', query_upper)
        tables.extend(join_matches)
        
        # Match UPDATE clause
        update_matches = re.findall(r'UPDATE\s+([a-zA-Z_][a-zA-Z0-9_]*)', query_upper)
        tables.extend(update_matches)
        
        # Match INSERT INTO clause
        insert_matches = re.findall(r'INSERT\s+INTO\s+([a-zA-Z_][a-zA-Z0-9_]*)', query_upper)
        tables.extend(insert_matches)
        
        return list(set(tables))
    
    def _is_safe_query(self, query: str) -> bool:
        """Check if query is safe (no DROP, DELETE without WHERE, etc.)"""
        query_upper = query.upper()
        
        # Dangerous operations
        dangerous_keywords = ['DROP', 'TRUNCATE', 'ALTER']
        for keyword in dangerous_keywords:
            if keyword in query_upper:
                return False
        
        # DELETE or UPDATE without WHERE
        if 'DELETE' in query_upper or 'UPDATE' in query_upper:
            if 'WHERE' not in query_upper:
                return False
        
        return True
    
    async def get_accessible_tables(self, user_id: str) -> List[str]:
        """Get list of tables accessible to user"""
        accessible = []
        
        for db_name, db_config in self.config.databases.items():
            for table, allowed_users in db_config.table_permissions.items():
                if not allowed_users or user_id in allowed_users:
                    accessible.append(f"{db_name}.{table}")
        
        return accessible
    
    async def get_table_schema(
        self,
        table_name: str,
        database: str
    ) -> Dict[str, Any]:
        """Get schema information for a table"""
        
        async with self.get_session(database) as session:
            # Get column information
            if self.config.databases[database].type == "sqlite":
                result = await session.execute(
                    text(f"PRAGMA table_info({table_name})")
                )
                columns = result.fetchall()
                return {
                    "table": table_name,
                    "columns": [
                        {
                            "name": col[1],
                            "type": col[2],
                            "nullable": not col[3],
                            "primary_key": bool(col[5])
                        }
                        for col in columns
                    ]
                }
            
            elif self.config.databases[database].type == "postgresql":
                result = await session.execute(text("""
                    SELECT 
                        column_name,
                        data_type,
                        is_nullable,
                        column_default
                    FROM information_schema.columns
                    WHERE table_name = :table_name
                    ORDER BY ordinal_position
                """), {"table_name": table_name})
                
                columns = result.fetchall()
                return {
                    "table": table_name,
                    "columns": [
                        {
                            "name": col[0],
                            "type": col[1],
                            "nullable": col[2] == "YES",
                            "default": col[3]
                        }
                        for col in columns
                    ]
                }
    
    async def list_tables(self, database: str) -> List[str]:
        """List all tables in a database"""
        
        async with self.get_session(database) as session:
            if self.config.databases[database].type == "sqlite":
                result = await session.execute(text(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                ))
            elif self.config.databases[database].type == "postgresql":
                result = await session.execute(text(
                    "SELECT tablename FROM pg_tables WHERE schemaname='public'"
                ))
            
            return [row[0] for row in result.fetchall()]
    
    async def execute_batch(
        self,
        queries: List[str],
        database: str,
        user_id: str
    ) -> List[List[Dict[str, Any]]]:
        """Execute multiple queries in a transaction"""
        
        results = []
        async with self.get_session(database) as session:
            for query in queries:
                if not await self._check_permissions(query, database, user_id):
                    raise PermissionError(f"Permission denied for query: {query}")
                
                if not self._is_safe_query(query):
                    raise ValueError(f"Unsafe query: {query}")
                
                result = await session.execute(text(query))
                
                if result.returns_rows:
                    columns = result.keys()
                    rows = result.fetchall()
                    results.append([dict(zip(columns, row)) for row in rows])
                else:
                    results.append([{"affected_rows": result.rowcount}])
        
        return results
    
    async def health_check(self) -> bool:
        """Check if all databases are accessible"""
        try:
            for db_name, engine in self.engines.items():
                async with engine.connect() as conn:
                    await conn.execute(text("SELECT 1"))
            return True
        except Exception as e:
            print(f"Database health check failed: {str(e)}")
            return False
    
    async def cleanup(self):
        """Close all database connections"""
        for db_name, engine in self.engines.items():
            await engine.dispose()
            print(f"✓ Closed {db_name} database connection")