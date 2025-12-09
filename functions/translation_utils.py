"""
Translation utilities using Google Cloud Translate API

This module handles language detection and translation between user languages and English.
"""

import os
import logging
from typing import Optional, List, Dict
from google.cloud import translate_v2 as translate
from firebase_admin import firestore

logger = logging.getLogger('translation_utils')
logger.setLevel(logging.INFO)

# Initialize Google Translate client
try:
    translate_client = translate.Client()
except Exception as e:
    logger.warning(f"Google Translate client initialization failed: {e}")
    translate_client = None


def get_supported_languages(db) -> List[Dict[str, str]]:
    """
    Retrieves supported languages from ss_language_support Firestore collection.
    
    Args:
        db: Firestore database client
        
    Returns:
        list: List of language dictionaries with 'code' and 'name'
        
    Example:
        [
            {"code": "en", "name": "English"},
            {"code": "ta", "name": "Tamil"},
            {"code": "ml", "name": "Malayalam"}
        ]
    """
    try:
        docs = db.collection('ss_language_support').stream()
        languages = []
        for doc in docs:
            lang_data = doc.to_dict()
            languages.append({
                'code': lang_data.get('code', doc.id),
                'name': lang_data.get('name', doc.id)
            })
        
        # If no languages in Firestore, return defaults
        if not languages:
            languages = [
                {"code": "en", "name": "English"},
                {"code": "ta", "name": "Tamil"},
                {"code": "ml", "name": "Malayalam"}
            ]
            logger.warning("No languages found in ss_language_support, using defaults")
        
        return languages
    except Exception as e:
        logger.error(f"Error fetching supported languages: {e}")
        # Return default languages
        return [
            {"code": "en", "name": "English"},
            {"code": "ta", "name": "Tamil"},
            {"code": "ml", "name": "Malayalam"}
        ]


def translate_text(text: str, target_language: str, source_language: str = None) -> str:
    """
    Translates text to target language using Google Translate API.
    
    Args:
        text: Text to translate
        target_language: ISO 639-1 language code (e.g., 'en', 'ta', 'ml')
        source_language: Optional source language code (auto-detect if None)
        
    Returns:
        str: Translated text
    """
    if not translate_client:
        logger.error("Google Translate client not initialized")
        return text
    
    # If target is English and text is already English, return as is
    if target_language == 'en' and not source_language:
        detected = detect_language(text)
        if detected == 'en':
            return text
    
    try:
        result = translate_client.translate(
            text,
            target_language=target_language,
            source_language=source_language
        )
        
        translated_text = result['translatedText']
        logger.info(f"Translated from {source_language or 'auto'} to {target_language}")
        return translated_text
        
    except Exception as e:
        logger.error(f"Translation failed: {e}")
        return text  # Return original text if translation fails


def detect_language(text: str) -> str:
    """
    Detects the language of the given text.
    
    Args:
        text: Text to detect language for
        
    Returns:
        str: ISO 639-1 language code
    """
    if not translate_client:
        return 'en'  # Default to English
    
    try:
        result = translate_client.detect_language(text)
        language_code = result['language']
        logger.info(f"Detected language: {language_code}")
        return language_code
    except Exception as e:
        logger.error(f"Language detection failed: {e}")
        return 'en'


def get_user_language(db, platform: str, user_id: str) -> Optional[str]:
    """
    Retrieves user's preferred language from Firestore.
    
    Args:
        db: Firestore database client
        platform: Platform name (facebook, instagram, whatsapp)
        user_id: User identifier
        
    Returns:
        str: Language code or None if not set
    """
    try:
        user_ref = db.collection(f"ss_{platform}_user_details").document(user_id)
        user_doc = user_ref.get()
        
        if user_doc.exists:
            user_data = user_doc.to_dict()
            return user_data.get('preferred_language')
        
        return None
    except Exception as e:
        logger.error(f"Error getting user language: {e}")
        return None


def set_user_language(db, platform: str, user_id: str, language_code: str) -> bool:
    """
    Sets user's preferred language in Firestore.
    
    Args:
        db: Firestore database client
        platform: Platform name (facebook, instagram, whatsapp)
        user_id: User identifier
        language_code: ISO 639-1 language code
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        user_ref = db.collection(f"ss_{platform}_user_details").document(user_id)
        user_ref.set({
            'preferred_language': language_code
        }, merge=True)
        
        logger.info(f"Set language {language_code} for {user_id} on {platform}")
        return True
    except Exception as e:
        logger.error(f"Error setting user language: {e}")
        return False


def is_language_supported(db, language_code: str) -> bool:
    """
    Checks if a language is supported based on ss_language_support collection.
    
    Args:
        db: Firestore database client
        language_code: ISO 639-1 language code
        
    Returns:
        bool: True if language is supported
    """
    supported_languages = get_supported_languages(db)
    supported_codes = [lang['code'] for lang in supported_languages]
    return language_code in supported_codes
