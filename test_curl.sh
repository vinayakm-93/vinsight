#!/bin/bash
cd backend
../.venv/bin/uvicorn main:app --port 8011 &
UVICORN_PID=$!
sleep 4
echo "Sending login request..."
curl -X POST http://127.0.0.1:8011/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"test@test.com", "password":"password"}' \
  -v
echo "Killing server..."
kill $UVICORN_PID
