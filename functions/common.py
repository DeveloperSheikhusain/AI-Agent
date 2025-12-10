"""
Common utilities for Firebase Functions

This module provides Firestore operations, message sending, and configuration.
"""

import os
import json
import logging
import requests
from firebase_admin import firestore, initialize_app, get_app
from bedrock_utils import invoke_bedrock_agent, get_config

logger = logging.getLogger('common')
logger.setLevel(logging.INFO)

# Lazy initialization variables
_db = None


def get_db():
    """
    Get Firestore client with lazy initialization.
    This prevents initialization during deployment analysis.
    """
    global _db
    if _db is None:
        try:
            app = get_app()
        except ValueError:
            app = initialize_app()
        _db = firestore.client()
    return _db




def get_remote_config(key: str) -> str:
    """
    Retrieves configuration values from environment variables.
    Wrapper around bedrock_utils.get_config for backward compatibility.
    """
    return get_config(key)


def send_facebook_message(recipient_id: str, text: str, quick_replies: list = None) -> None:
    """
    Sends a message to Facebook Messenger with optional quick reply buttons.
    
    Args:
        recipient_id: Facebook user ID
        text: Message text to send
        quick_replies: Optional list of quick reply options
                      Format: [{"title": "English", "payload": "LANG_en"}, ...]
    """
    page_access_token = get_remote_config('FACEBOOK_PAGE_ACCESS_TOKEN')
    if not page_access_token:
        logger.error("Facebook Page Access Token missing.")
        return

    url = f"https://graph.facebook.com/v19.0/me/messages?access_token={page_access_token}"
    
    message_data = {"text": text}
    
    # Add quick replies if provided
    if quick_replies:
        message_data["quick_replies"] = [
            {
                "content_type": "text",
                "title": qr["title"],
                "payload": qr["payload"]
            }
            for qr in quick_replies
        ]
    
    payload = {
        "recipient": {"id": recipient_id},
        "message": message_data
    }
    
    try:
        r = requests.post(url, json=payload)
        r.raise_for_status()
        logger.info(f"Sent Facebook message to {recipient_id}")
    except Exception as e:
        logger.error(f"Failed to send Facebook message: {e}")


def send_instagram_message(recipient_id: str, text: str, quick_replies: list = None) -> None:
    """
    Sends a message to Instagram via Messenger API with optional quick reply buttons.
    
    Args:
        recipient_id: Instagram user ID (IGSID)
        text: Message text to send
        quick_replies: Optional list of quick reply options
    """
    # Instagram uses same endpoint but can have different token
    page_access_token = get_remote_config('INSTAGRAM_PAGE_ACCESS_TOKEN') or \
                       get_remote_config('FACEBOOK_PAGE_ACCESS_TOKEN')
    
    if not page_access_token:
        logger.error("Instagram/Facebook Page Access Token missing.")
        return

    url = f"https://graph.facebook.com/v19.0/me/messages?access_token={page_access_token}"
    
    message_data = {"text": text}
    
    # Add quick replies if provided
    if quick_replies:
        message_data["quick_replies"] = [
            {
                "content_type": "text",
                "title": qr["title"],
                "payload": qr["payload"]
            }
            for qr in quick_replies
        ]
    
    payload = {
        "recipient": {"id": recipient_id},
        "message": message_data
    }
    
    try:
        r = requests.post(url, json=payload)
        r.raise_for_status()
        logger.info(f"Sent Instagram message to {recipient_id}")
    except Exception as e:
        logger.error(f"Failed to send Instagram message: {e}")


def send_whatsapp_message(recipient_phone: str, text: str, buttons: list = None) -> None:
    """
    Sends a message to WhatsApp via Cloud API with optional buttons.
    
    Args:
        recipient_phone: Recipient phone number
        text: Message text to send
        buttons: Optional list of button options
                Format: [{"id": "lang_en", "title": "English"}, ...]
    """
    access_token = get_remote_config('WHATSAPP_ACCESS_TOKEN') or \
                   get_remote_config('FACEBOOK_PAGE_ACCESS_TOKEN')
    phone_number_id = get_remote_config('WHATSAPP_PHONE_NUMBER_ID')
    
    if not access_token or not phone_number_id:
        logger.error("WhatsApp configuration missing.")
        return

    url = f"https://graph.facebook.com/v19.0/{phone_number_id}/messages"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }
    
    # Build payload based on whether buttons are provided
    if buttons and len(buttons) <= 3:  # WhatsApp supports max 3 quick reply buttons
        payload = {
            "messaging_product": "whatsapp",
            "to": recipient_phone,
            "type": "interactive",
            "interactive": {
                "type": "button",
                "body": {"text": text},
                "action": {
                    "buttons": [
                        {"type": "reply", "reply": {"id": btn["id"], "title": btn["title"]}}
                        for btn in buttons[:3]  # Max 3 buttons
                    ]
                }
            }
        }
    else:
        # Regular text message
        payload = {
            "messaging_product": "whatsapp",
            "to": recipient_phone,
            "type": "text",
            "text": {"body": text}
        }
    
    try:
        r = requests.post(url, json=payload, headers=headers)
        r.raise_for_status()
        logger.info(f"Sent WhatsApp message to {recipient_phone}")
    except Exception as e:
        logger.error(f"Failed to send WhatsApp message: {e}")


def save_user_details(platform: str, user_data: dict) -> None:
    """
    Saves or updates user details in Firestore.
    
    Args:
        platform: Platform name (facebook, instagram, whatsapp)
        user_data: Dictionary containing user information
    """
    collection_name = f"ss_{platform}_user_details"
    user_id = user_data.get('user_id')
    
    if not user_id:
        logger.error("User ID missing in user_data.")
        return

    user_ref = get_db().collection(collection_name).document(user_id)
    
    # Add timestamps
    now = firestore.SERVER_TIMESTAMP
    
    # Check if user exists
    doc = user_ref.get()
    if not doc.exists:
        user_data['first_interaction'] = now
        user_data['message_count'] = 1
    else:
        user_data['message_count'] = firestore.Increment(1)
    
    user_data['last_interaction'] = now
    
    user_ref.set(user_data, merge=True)
    logger.info(f"Saved user details for {user_id} on {platform}")


def save_chat_message(platform: str, user_id: str, message: dict) -> None:
    """
    Stores a chat message in Firestore subcollection.
    Structure: ss_{platform}_chat_history/{user_id}/messages/{message_id}
    
    Args:
        platform: Platform name (facebook, instagram, whatsapp)
        user_id: User identifier
        message: Message data dictionary
    """
    collection_ref = get_db().collection(f"ss_{platform}_chat_history") \
                       .document(user_id) \
                       .collection('messages')
    
    message['timestamp'] = firestore.SERVER_TIMESTAMP
    collection_ref.add(message)
    logger.info(f"Saved chat message for {user_id} on {platform}")


def get_chat_context(platform: str, user_id: str, limit: int = 10) -> list:
    """
    Retrieves recent chat history for a user.
    
    Args:
        platform: Platform name (facebook, instagram, whatsapp)
        user_id: User identifier
        limit: Maximum number of messages to retrieve
        
    Returns:
        list: List of message dictionaries in chronological order
    """
    collection_ref = get_db().collection(f"ss_{platform}_chat_history") \
                       .document(user_id) \
                       .collection('messages')
    
    # Order by timestamp descending, then reverse for chronological order
    query_ref = collection_ref.order_by('timestamp', direction=firestore.Query.DESCENDING).limit(limit)
    docs = query_ref.stream()
    
    messages = []
    for doc in docs:
        msg = doc.to_dict()
        # Convert timestamp to string for JSON serialization
        if msg.get('timestamp'):
            msg['timestamp'] = msg['timestamp'].isoformat() if hasattr(msg['timestamp'], 'isoformat') else str(msg['timestamp'])
        messages.append(msg)
    
    logger.info(f"Retrieved {len(messages)} messages for {user_id} on {platform}")
    return messages[::-1]  # Reverse to chronological order
