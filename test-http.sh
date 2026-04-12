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
    local _arg=$2
    response=$(curl -sX POST http://localhost:$port/mcp \
                    -H "Content-Type: application/json" \
                    -H "Accept: application/json, text/event-stream" \
                    -H "mcp-session-id: $SESSION" \
                    -d '{"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":"'"$_tool"'","arguments":{'"$_arg"'}}}')
    evt=$(echo "$response"|grep ^event:|sed 's/^event: //')
    echo "---- event type: $evt"
    echo "$response"|grep ^data:|sed 's/^data: //'|jq -r .result.content[0].text
} 

while read -p 'wilma-bot> ' cmd param; do

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
            if [ ! "$param" ]; then
                echo "Fetching messages.."
                tool get_messages
            else
                echo "Fetching message $param.."
                tool get_message '"message_id":"'"$param"'"'
            fi
            ;;
        sch*)
            echo "Fetching schedule.."
            tool get_schedule
            ;;
        not*)
            if [ ! "$param" ]; then
                echo "Fetching notices.."
                tool get_notices
            else
                echo "Fetching notice $param.."
                tool get_notice '"notice_id":"'"$param"'"'
            fi
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
