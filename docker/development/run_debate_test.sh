#!/bin/bash
# Create and run a test debate
DEBATE_ID=$(curl -s -X POST http://localhost:8000/api/v1/debates/v2 \
  -H "Content-Type: application/json" \
  -d @test_debate.json | jq -r '.id')

echo "Created debate: $DEBATE_ID"

# Run the debate and capture output
curl -N "http://localhost:8000/api/v1/debates/v2/$DEBATE_ID/next-turn" 2>&1 | tee debate_full_output.txt
