# Docker Deployment Guide - Luxury Item Appraisal System

This guide provides step-by-step instructions for deploying the Luxury Item Appraisal System using Docker containers. Following these instructions will help you set up both frontend and backend components of the application.

## Prerequisites

- [Docker](https://docs.docker.com/get-docker/) and [Docker Compose](https://docs.docker.com/compose/install/) installed on your system
- Git to clone the repository
- Valid API keys for OpenAI and/or Anthropic if you want to use the LLM features

## Project Structure

The project consists of two main components:

- **Frontend**: Angular application for the user interface
- **Backend**: FastAPI application that handles business logic and integrates with LLM services

## Quick Start

### Clone the Repository

### Configuration

The backend directory already contains a `.env` file with configuration settings. You should replace the API keys with your own:

1. Navigate to the backend directory:
   ```bash
   cd backend
   ```

2. Create a `.env` file to replace the existing API keys with your own:
   ```bash
   # Example .env file content
   OPENAI_API_KEY=your_openai_api_key_here
   LLM_OPENAI_API_KEY=your_openai_api_key_here
   PERPLEXITY_API_KEY=your_perplexity_api_key_here
   OPENAI_MODEL_NAME=gpt-4o
   
   # Add any other required environment variables
   ```

3. Return to the project root directory:
   ```bash
   cd ..
   ```

### Building and Running with Docker Compose

The easiest way to deploy the entire application is using Docker Compose:

```bash
docker-compose up -d
```

This command will:
1. Build both frontend and backend Docker images
2. Create a shared network for container communication
3. Set up necessary volumes for data persistence
4. Start both services in detached mode

### Access the Application

Once the containers are running, you can access:

- **Frontend**: http://localhost
- **Backend API Docs**: http://localhost:8000/docs

## Manual Deployment (without Docker Compose)

If you prefer to manage containers manually, follow these steps:

### 1. Create a Docker Network

```bash
docker network create lux-appraisal-network
```

### 2. Create Data Volume

```bash
docker volume create backend-data
```

### 3. Build and Run Backend

```bash
# Navigate to the backend directory
cd backend

# Build the backend image
docker build -t lux-backend:latest .

# Run the backend container with the .env file
docker run -d \
  --name lux-backend \
  --hostname lux-backend \
  --network lux-appraisal-network \
  -p 8000:8000 \
  -v backend-data:/app/uploads \
  -v backend-data:/app/reports \
  --env-file .env \
  lux-backend:latest
```

### 4. Build and Run Frontend

```bash
# Navigate to the frontend directory
cd ../frontend

# Build the frontend image
docker build -t lux-frontend:latest .

# Run the frontend container
docker run -d \
  --name lux-frontend \
  --network lux-appraisal-network \
  -p 80:80 \
  lux-frontend:latest
```

## Stopping the Application

### Using Docker Compose

```bash
docker-compose down
```

To also remove volumes and persistent data:
```bash
docker-compose down -v
```

### Using Manual Container Management

```bash
docker stop lux-frontend lux-backend
docker rm lux-frontend lux-backend
```

## Troubleshooting

### Check Container Status

```bash
docker ps -a
```

### View Container Logs

```bash
# Frontend logs
docker logs lux-frontend

# Backend logs
docker logs lux-backend
```

### Common Issues and Solutions

1. **Frontend can't connect to backend**:
   - Ensure both containers are on the same network
   - Check if the backend container is running
   - Verify the nginx.conf configuration in the frontend container

2. **Missing dependencies in backend**:
   - If you encounter missing package errors, you might need to update the requirements.txt file and rebuild the backend image

3. **Port conflicts**:
   - If ports 80 or 8000 are already in use, modify the port mappings in the docker-compose.yml file or docker run commands

4. **API key issues**:
   - If the LLM functionality isn't working, check that the API keys in your .env file are valid and properly formatted

## Updating the Application

### Pull Latest Code

```bash
git pull
```

### Rebuild and Restart Containers

```bash
docker-compose up -d --build
```

## Environment Variables

The backend uses the following environment variables from the .env file:

- `OPENAI_API_KEY`: OpenAI API key for model access
- `LLM_OPENAI_API_KEY`: Alternative OpenAI API key
- `ANTHROPIC_API_KEY`: Anthropic API key for Claude models
- `PERPLEXITY_API_KEY`: Perplexity API key
- `OPENAI_MODEL_NAME`: Name of the OpenAI model to use (e.g., gpt-4o)
- `ENVIRONMENT`: Set the running environment (`development`/`production`)
- `DEBUG`: Enable debug logs (`True`/`False`)

## Data Persistence

The application uses Docker volumes to persist data:

- `backend-data`: Stores uploaded files and generated reports

## Application Architecture

The application consists of:

1. **Angular Frontend**: Provides the user interface for interacting with the appraisal system
2. **FastAPI Backend**: Provides REST API endpoints and integrates with LLM services
3. **Nginx**: Serves the frontend static files and proxies API requests to the backend
4. **LLM Integration**: Connects to OpenAI and/or Anthropic for appraisal generation

## Security Considerations

1. Never commit API keys to the code repository
2. For production environments, consider adding HTTPS support
3. Restrict access to the Docker daemon and containers

## License

[License information goes here] 
