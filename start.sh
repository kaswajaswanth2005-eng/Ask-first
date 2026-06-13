#!/bin/bash
# Start FastAPI backend in the background on port 8000
uvicorn main:app --host 0.0.0.0 --port 8000 &

# Wait for 2 seconds to let the API boot up
sleep 2

# Start Streamlit frontend on the public port Render gives us
streamlit run app.py --server.port $PORT --server.address 0.0.0.0
