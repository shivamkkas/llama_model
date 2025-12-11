
from config.config import Config
from app.server import MCPServer
if __name__ == "__main__":
    # Load configuration
    config = Config.from_file("./config.yaml")
    
    # Create and run server
    server = MCPServer(config)
    server.run()