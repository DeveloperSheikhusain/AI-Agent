from firebase_functions import https_fn
from firebase_admin import initialize_app
from common import invoke_bedrock_agent, save_user_details, save_chat_message, get_chat_context, db
from common import get_remote_config, send_facebook_message, send_instagram_message, send_whatsapp_message
import json

@https_fn.on_request()
def agent_invoke(req: https_fn.Request) -> https_fn.Response:
    """
    Direct API to invoke the Bedrock Agent.
    """
    if req.method != "POST":
        return https_fn.Response("Method not allowed", status=405)

    try:
        data = req.get_json(silent=True)
        if not data:
            return https_fn.Response("Invalid JSON body", status=400)

        user_id = data.get("user_id")
        message = data.get("message")
        session_id = data.get("session_id") or user_id

        if not user_id or not message:
            return https_fn.Response("Missing user_id or message", status=400)

        result = invoke_bedrock_agent(message, session_id, user_id)
        
        return https_fn.Response(json.dumps(result), mimetype='application/json')
    except Exception as e:
        return https_fn.Response(f"Error: {str(e)}", status=500)

@https_fn.on_request()
def users_list(req: https_fn.Request) -> https_fn.Response:
    """
    Get users list for a specific platform.
    Query param: platform (facebook, instagram, whatsapp)
    """
    platform = req.args.get('platform')
    if platform not in ['facebook', 'instagram', 'whatsapp']:
        return https_fn.Response("Invalid or missing platform. Options: facebook, instagram, whatsapp", status=400)
    
    try:
        collection_name = f"ss_{platform}_user_details"
        docs = db.collection(collection_name).stream()
        
        users = []
        for doc in docs:
            users.append(doc.to_dict())
            
        return https_fn.Response(json.dumps(users, default=str), mimetype='application/json')
    except Exception as e:
        return https_fn.Response(f"Error fetching users: {str(e)}", status=500)

@https_fn.on_request()
def chat_history(req: https_fn.Request) -> https_fn.Response:
    """
    Get chat history for a user.
    Query params: user_id, platform, limit
    """
    user_id = req.args.get('user_id')
    platform = req.args.get('platform')
    limit = req.args.get('limit', 50)
    
    if not user_id or not platform:
        return https_fn.Response("Missing user_id or platform", status=400)
        
    if platform not in ['facebook', 'instagram', 'whatsapp']:
        return https_fn.Response("Invalid platform", status=400)
        
    try:
        limit = int(limit) if limit else 50
        history = get_chat_context(platform, user_id, limit)
        return https_fn.Response(json.dumps(history, default=str), mimetype='application/json')
    except Exception as e:
        return https_fn.Response(f"Error fetching history: {str(e)}", status=500)

@https_fn.on_request()
def webhook_facebook(req: https_fn.Request) -> https_fn.Response:
    """
    Facebook Messenger webhook endpoint with multi-language support.
    """
    from language_handler import process_message_with_translation
    
    # Webhook verification
    if req.method == "GET":
        mode = req.args.get("hub.mode")
        token = req.args.get("hub.verify_token")
        challenge = req.args.get("hub.challenge")
        
        verify_token = get_remote_config("FACEBOOK_VERIFY_TOKEN")
        
        if mode == "subscribe" and token == verify_token:
            return https_fn.Response(challenge)
        return https_fn.Response("Forbidden", status=403)

    # Handle incoming messages
    try:
        data = req.get_json(silent=True)
        if data.get("object") == "page":
            for entry in data.get("entry", []):
                for messaging_event in entry.get("messaging", []):
                    sender_id = messaging_event.get("sender", {}).get("id")
                    message = messaging_event.get("message", {})
                    message_text = message.get("text")
                    quick_reply_payload = message.get("quick_reply", {}).get("payload")
                    
                    if sender_id and message_text:
                        # Save user details
                        save_user_details("facebook", {
                            "user_id": sender_id,
                            "platform_user_id": sender_id
                        })
                        
                        # Save incoming message
                        save_chat_message("facebook", sender_id, {
                            "user_id": sender_id,
                            "sender": "user",
                            "message_text": message_text,
                            "session_id": sender_id,
                            "metadata": {"platform_message_id": message.get("mid")}
                        })
                        
                        # Process with language translation
                        result = process_message_with_translation(
                            db, "facebook", sender_id, message_text, quick_reply_payload
                        )
                        
                        response_text = result.get("response")
                        quick_replies = result.get("quick_replies")
                        
                        # Send reply
                        if response_text:
                            send_facebook_message(sender_id, response_text, quick_replies)
                            
                            # Save outgoing message
                            save_chat_message("facebook", sender_id, {
                                "user_id": sender_id,
                                "sender": "agent",
                                "message_text": response_text,
                                "session_id": sender_id
                            })
                            
            return https_fn.Response("EVENT_RECEIVED", status=200)
        return https_fn.Response("Not a page event", status=404)
    except Exception as e:
        return https_fn.Response(f"Error: {str(e)}", status=500)

@https_fn.on_request()
def webhook_instagram(req: https_fn.Request) -> https_fn.Response:
    """
    Instagram DM webhook endpoint.
    """
    # Webhook verification
    if req.method == "GET":
        mode = req.args.get("hub.mode")
        token = req.args.get("hub.verify_token")
        challenge = req.args.get("hub.challenge")
        
        verify_token = get_remote_config("FACEBOOK_VERIFY_TOKEN")
        
        if mode == "subscribe" and token == verify_token:
            return https_fn.Response(challenge)
        return https_fn.Response("Forbidden", status=403)

    # Handle incoming messages
    try:
        data = req.get_json(silent=True)
        if data.get("object") in ["instagram", "page"]:
            for entry in data.get("entry", []):
                for messaging_event in entry.get("messaging", []):
                    sender_id = messaging_event.get("sender", {}).get("id")
                    message = messaging_event.get("message", {})
                    message_text = message.get("text")
                    
                    if sender_id and message_text:
                        save_user_details("instagram", {
                            "user_id": sender_id,
                            "platform_user_id": sender_id
                        })
                        
                        save_chat_message("instagram", sender_id, {
                            "user_id": sender_id,
                            "sender": "user",
                            "message_text": message_text,
                            "session_id": sender_id,
                            "metadata": {"platform_message_id": message.get("mid")}
                        })
                        
                        result = invoke_bedrock_agent(message_text, sender_id, sender_id)
                        response_text = result.get("response")
                        
                        if response_text:
                            send_instagram_message(sender_id, response_text)
                            
                            save_chat_message("instagram", sender_id, {
                                "user_id": sender_id,
                                "sender": "agent",
                                "message_text": response_text,
                                "session_id": sender_id
                            })
                            
            return https_fn.Response("EVENT_RECEIVED", status=200)
        return https_fn.Response("Not an instagram event", status=404)
    except Exception as e:
        return https_fn.Response(f"Error: {str(e)}", status=500)

@https_fn.on_request()
def webhook_whatsapp(req: https_fn.Request) -> https_fn.Response:
    """
    WhatsApp Business webhook endpoint.
    """
    # Webhook verification
    if req.method == "GET":
        mode = req.args.get("hub.mode")
        token = req.args.get("hub.verify_token")
        challenge = req.args.get("hub.challenge")
        
        verify_token = get_remote_config("FACEBOOK_VERIFY_TOKEN")
        
        if mode == "subscribe" and token == verify_token:
            return https_fn.Response(challenge)
        return https_fn.Response("Forbidden", status=403)

    # Handle incoming messages
    try:
        data = req.get_json(silent=True)
        if data.get("object") == "whatsapp_business_account":
            for entry in data.get("entry", []):
                for change in entry.get("changes", []):
                    value = change.get("value", {})
                    if "messages" in value:
                        for message in value.get("messages", []):
                            sender_phone = message.get("from")
                            message_body = message.get("text", {}).get("body")
                            
                            if sender_phone and message_body:
                                # Extract contact name if available
                                contacts = value.get("contacts", [{}])
                                profile_name = contacts[0].get("profile", {}).get("name") if contacts else None
                                
                                save_user_details("whatsapp", {
                                    "user_id": sender_phone,
                                    "phone_number": sender_phone,
                                    "profile_name": profile_name
                                })
                                
                                save_chat_message("whatsapp", sender_phone, {
                                    "user_id": sender_phone,
                                    "sender": "user",
                                    "message_text": message_body,
                                    "session_id": sender_phone,
                                    "metadata": {"platform_message_id": message.get("id")}
                                })
                                
                                result = invoke_bedrock_agent(message_body, sender_phone, sender_phone)
                                response_text = result.get("response")
                                
                                if response_text:
                                    send_whatsapp_message(sender_phone, response_text)
                                    
                                    save_chat_message("whatsapp", sender_phone, {
                                        "user_id": sender_phone,
                                        "sender": "agent",
                                        "message_text": response_text,
                                        "session_id": sender_phone
                                    })
                                    
            return https_fn.Response("EVENT_RECEIVED", status=200)
        return https_fn.Response("Not a whatsapp event", status=404)
    except Exception as e:
        return https_fn.Response(f"Error: {str(e)}", status=500)