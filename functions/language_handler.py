"""
Language workflow handler

This module manages the language selection workflow and message translation pipeline.
"""

import logging
from typing import Dict, Optional, Tuple
from translation_utils import (
    get_supported_languages,
    translate_text,
    get_user_language,
    set_user_language,
    is_language_supported
)
from bedrock_utils import invoke_bedrock_agent

logger = logging.getLogger('language_handler')
logger.setLevel(logging.INFO)


def create_language_selection_prompt(db) -> Tuple[str, list]:
    """
    Creates language selection prompt with quick reply buttons.
    
    Args:
        db: Firestore database client
        
    Returns:
        tuple: (prompt_text, quick_replies_list)
    """
    supported_languages = get_supported_languages(db)
    
    prompt_text = "Welcome! 🌍\n\nWhat's your preferred language?\nஉங்கள் விருப்ப மொழி என்ன?\nനിങ്ങളുടെ ഇഷ്ടമുള്ള ഭാഷ എന്താണ്?"
    
    # Create quick replies for Facebook/Instagram
    quick_replies = [
        {
            "title": lang['name'],
            "payload": f"LANG_{lang['code']}"
        }
        for lang in supported_languages
    ]
    
    # Create buttons for WhatsApp (max 3)
    buttons = [
        {
            "id": f"lang_{lang['code']}",
            "title": lang['name']
        }
        for lang in supported_languages[:3]  # WhatsApp max 3 buttons
    ]
    
    return prompt_text, quick_replies, buttons


def is_language_selection_response(message_text: str, payload: str = None) -> Optional[str]:
    """
    Checks if the message is a language selection response.
    
    Args:
        message_text: The message text
        payload: Optional quick reply payload
        
    Returns:
        str: Language code if this is a language selection, None otherwise
    """
    # Check payload first (quick reply/button)
    if payload:
        if payload.startswith("LANG_"):
            return payload.replace("LANG_", "")
        if payload.startswith("lang_"):
            return payload.replace("lang_", "")
    
    # Check message text for language names or codes
    text_lower = message_text.lower().strip()
    language_map = {
        'english': 'en',
        'tamil': 'ta',
        'malayalam': 'ml',
        'en': 'en',
        'ta': 'ta',
        'ml': 'ml'
    }
    
    return language_map.get(text_lower)


def process_message_with_translation(
    db,
    platform: str,
    user_id: str,
    message_text: str,
    payload: str = None
) -> Dict[str, str]:
    """
    Processes a user message with language translation and agent invocation.
    
    Workflow:
    1. Check if user has selected language
    2. If not, prompt for language selection
    3. If language selection response, save and confirm
    4. Otherwise: Translate to English → Invoke Agent → Translate back
    
    Args:
        db: Firestore database client
        platform: Platform name (facebook, instagram, whatsapp)
        user_id: User identifier
        message_text: User's message text
        payload: Optional payload from quick reply/button
        
    Returns:
        dict: {
            'response': str,  # Text to send back to user
            'quick_replies': list,  # Optional quick replies
            'buttons': list  # Optional WhatsApp buttons
        }
    """
    user_language = get_user_language(db, platform, user_id)
    
    # Case 1: User hasn't selected language yet
    if not user_language:
        # Check if this message is a language selection
        selected_lang = is_language_selection_response(message_text, payload)
        
        if selected_lang and is_language_supported(db, selected_lang):
            # Save language selection
            set_user_language(db, platform, user_id, selected_lang)
            
            # Send confirmation in their language
            confirmations = {
                'en': '✅ Language set to English! How can I help you today?',
                'ta': '✅ மொழி தமிழ் என அமைக்கப்பட்டது! இன்று நான் உங்களுக்கு எப்படி உதவ முடியும்?',
                'ml': '✅ ഭാഷ മലയാളം ആയി സജ്ജമാക്കി! ഇന്ന് ഞാൻ നിങ്ങളെ എങ്ങനെ സഹായിക്കും?'
            }
            
            return {
                'response': confirmations.get(selected_lang, confirmations['en']),
                'quick_replies': None,
                'buttons': None
            }
        else:
            # Show language selection prompt
            prompt_text, quick_replies, buttons = create_language_selection_prompt(db)
            return {
                'response': prompt_text,
                'quick_replies': quick_replies,
                'buttons': buttons
            }
    
    # Case 2: User has language selected - process with translation
    try:
        # Step 1: Translate user message to English (if not already English)
        if user_language != 'en':
            english_message = translate_text(message_text, target_language='en', source_language=user_language)
            logger.info(f"Translated '{message_text}' to '{english_message}'")
        else:
            english_message = message_text
        
        # Step 2: Invoke AWS Bedrock Agent with English message
        agent_result = invoke_bedrock_agent(english_message, session_id=user_id, user_id=user_id)
        english_response = agent_result.get('response', '')
        
        # Step 3: Translate response back to user's language (if not English)
        if user_language != 'en':
            translated_response = translate_text(english_response, target_language=user_language, source_language='en')
            logger.info(f"Translated response to {user_language}")
        else:
            translated_response = english_response
        
        return {
            'response': translated_response,
            'quick_replies': None,
            'buttons': None
        }
        
    except Exception as e:
        logger.error(f"Error in translation pipeline: {e}")
        
        # Fallback error message in user's language
        error_messages = {
            'en': '❌ Sorry, I encountered an error. Please try again.',
            'ta': '❌ மன்னிக்கவும், ஒரு பிழை ஏற்பட்டது. மீண்டும் முயற்சிக்கவும்.',
            'ml': '❌ ക്ഷമിക്കണം, എനിക്ക് ഒരു പിശക് നേരിട്ടു. വീണ്ടും ശ്രമിക്കുക.'
        }
        
        return {
            'response': error_messages.get(user_language, error_messages['en']),
            'quick_replies': None,
            'buttons': None
        }
