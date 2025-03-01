#!/bin/bash

# Start the Next.js server
echo "Starting Neuromansui Report Server..."
cd neuromansui-server
# Use -H 0.0.0.0 to make the server listen on all network interfaces
npm run dev -- -H 0.0.0.0 -p 3000

# Print usage information
echo ""
echo "Neuromansui Report Server is running at http://localhost:3000"
echo ""
echo "To generate reports, run the neuromansui tool in another terminal with:"
echo "python -m neuromansui.main --prompt <prompt_name> --save-iterations --dark-mode"
echo ""
echo "Press Ctrl+C to stop the server"

# Handle termination
trap "kill $SERVER_PID; echo 'Server stopped.'; exit 0" SIGINT

# Keep the script running
wait 