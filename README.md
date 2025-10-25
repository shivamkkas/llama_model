# llama_model
# Ollama RAG UI - Frontend

Modern React UI for Ollama RAG API with document management and conversation features.

## Features

- 💬 Chat interface with conversation management
- 📚 Document upload and RAG-powered search
- 🎯 Multiple model support
- 🌙 Dark mode UI
- 📱 Responsive design
- 🚀 Optimized Docker deployment

## Local Development

### Prerequisites
- Node.js 18+ 
- npm or yarn

### Setup

1. Install dependencies:
```bash
npm install
```

2. Create `.env` file:
```bash
cp .env.example .env
```

3. Update `.env` with your backend URL:
```env
VITE_API_BASE_URL=http://localhost:8000
```

4. Start development server:
```bash
npm run dev
```

5. Open http://localhost:3000

## Docker Deployment

### Build and run:
```bash
docker build -t ollama-rag-ui .
docker run -p 3005:80 ollama-rag-ui
```

### With docker-compose (recommended):
```bash
docker-compose up -d
```

## Production Build

```bash
npm run build
```

Build output will be in `build/` directory.

## Environment Variables

- `VITE_API_BASE_URL` - Backend API URL (default: http://localhost:8000)
- `VITE_OLLAMA_HOST` - Ollama host URL (optional)

## Tech Stack

- React 18
- Vite
- Tailwind CSS
- Lucide React (icons)
- Nginx (production)

## API Endpoints Used

- `GET /health` - Health check
- `GET /api/conversations` - List conversations
- `POST /api/conversations` - Create conversation
- `GET /api/conversations/{id}` - Get conversation
- `DELETE /api/conversations/{id}` - Delete conversation
- `POST /api/chat` - Send message
- `POST /api/rag/query` - RAG query
- `GET /api/documents` - List documents
- `POST /api/upload` - Upload document
- `DELETE /api/documents/{hash}` - Delete document
- `GET /api/stats` - Get statistics

## License

MIT
```

---

## 14. .gitignore
```
# Dependencies
node_modules
/.pnp
.pnp.js

# Testing
/coverage

# Production
/build
/dist

# Misc
.DS_Store
.env
.env.local
.env.development.local
.env.test.local
.env.production.local
