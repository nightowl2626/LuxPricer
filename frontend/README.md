# Lux Appraisal Frontend

A chat interface for the Lux Appraisal system. This Angular application provides a ChatGPT-like interface to interact with the Lux Appraisal backend API.

## Features

- Chat-based interface for interacting with the appraisal system
- Submit queries to appraise luxury items
- View detailed appraisal reports
- Examine debug information and API response details

## Prerequisites

- Node.js (v18+)
- Angular CLI
- Running Lux Appraisal backend server

## Getting Started

1. Install dependencies:
   ```bash
   npm install
   ```

2. Start the development server:
   ```bash
   npm start
   ```

3. Open your browser to `http://localhost:4200`

## Usage

1. Ensure the backend API server is running at `http://localhost:8000`
2. Enter a query describing an item to appraise, for example:
   - "Value of my excellent condition medium black lambskin Chanel Classic Flap?"
   - "What's the value of a Rolex Submariner Date from 2018 in good condition?"
3. View the detailed appraisal report
4. Click "Show Details" to see the technical details of the API response

## Build for Production

```bash
npm run build
```

The build artifacts will be stored in the `dist/` directory. 