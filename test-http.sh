#!/bin/bash

# Use: $0 <port>

port=${1:-6060}


SESSION=$(curl -s -X POST http://localhost:$port/mcp \
               -H "Content-Type: application/json" \
               -H "Accept: application/json, text/event-stream" \
               -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"curl","version":"0.1"}}}' \
               -D - | grep -i mcp-session-id | awk '{print $2}' | tr -d '\r')

if [ ! "$SESSION" ]; then
    echo "Failed to fetch session id"
    exit 1
fi

echo "Session: $SESSION"

function tool() {
    local _tool=$1
    curl -sX POST http://localhost:$port/mcp \
         -H "Content-Type: application/json" \
         -H "Accept: application/json, text/event-stream" \
         -H "mcp-session-id: $SESSION" \
         -d '{"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":"'"$_tool"'","arguments":{}}}'
} 

while read -p 'wilma-bot> ' cmd; do

    case $cmd in
        li*)
            echo "Fetching tool list.."
            curl -X POST http://localhost:$port/mcp \
                 -H "Content-Type: application/json" \
                 -H "Accept: application/json, text/event-stream" \
                 -H "mcp-session-id: $SESSION" \
                 -d '{"jsonrpc":"2.0","id":2,"method":"tools/list","params":{}}'
            ;;
        mes*)
            echo "Fetching messages.."
            tool get_messages
            ;;
        sch*)
            echo "Fetching schedule.."
            tool get_schedule
            ;;
        not*)
            echo "Fetching notices.."
            tool get_notices
            ;;
        *)
            echo "Commands:"
            echo -e "\tlist     - list the tools"
            echo -e "\tmessages - call get_messages()"
            echo -e "\tschedule - call get_schedula()"
            echo -e "\tnotices  - call get_notices()"
            ;;
    esac
done
