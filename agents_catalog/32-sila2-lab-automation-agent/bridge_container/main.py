"""Main entry point for Bridge Container"""
import uvicorn

if __name__ == "__main__":
    uvicorn.run("mcp_server:app", host="0.0.0.0", port=8080, reload=False)
