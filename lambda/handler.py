import json
import os
import uuid

import boto3
from boto3.dynamodb.conditions import Key

table = boto3.resource("dynamodb").Table(os.environ["TABLE_NAME"])


def resp(code, body):
    return {
        "statusCode": code,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
        },
        "body": json.dumps(body),
    }


def lambda_handler(event, context):
    # "sub" is the unique user id inside the Cognito token.
    # Using it as the partition key means users only ever see their own items.
    user = event["requestContext"]["authorizer"]["claims"]["sub"]
    method = event["httpMethod"]
    todo_id = (event.get("pathParameters") or {}).get("id")

    try:
        body = json.loads(event.get("body") or "{}")
    except json.JSONDecodeError:
        return resp(400, {"error": "Body must be valid JSON"})

    if method == "GET" and not todo_id:
        r = table.query(KeyConditionExpression=Key("userId").eq(user))
        return resp(200, r["Items"])

    if method == "POST":
        title = body.get("title", "").strip()
        if not title:
            return resp(400, {"error": "title is required"})
        item = {
            "userId": user,
            "todoId": str(uuid.uuid4()),
            "title": title,
            "status": "open",
        }
        table.put_item(Item=item)
        return resp(201, item)

    if method == "PUT" and todo_id:
        table.update_item(
            Key={"userId": user, "todoId": todo_id},
            UpdateExpression="SET title = :t, #s = :s",
            ExpressionAttributeNames={"#s": "status"},
            ExpressionAttributeValues={
                ":t": body.get("title", ""),
                ":s": body.get("status", "open"),
            },
        )
        return resp(200, {"updated": todo_id})

    if method == "DELETE" and todo_id:
        table.delete_item(Key={"userId": user, "todoId": todo_id})
        return resp(200, {"deleted": todo_id})

    return resp(400, {"error": "Bad request"})
