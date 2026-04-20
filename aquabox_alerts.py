#!/usr/bin/env python3
"""
AquaBox Alerts Display
- Fetches bearer token from AquaGen API
- Fetches daily alerts
- Displays alerts on the 5-inch HDMI screen via GTK
- Auto-refreshes every 60 seconds
- Scrollable alert cards with color-coded importance
"""

import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, Gdk, GLib, Pango, GdkPixbuf
import cairo, math as _math, random as _random
import requests
import json
import time
import threading
import signal
import sys
import os
import subprocess
from datetime import datetime

# ==================== CONFIG ====================
AUTH_URL = "https://prod-aquagen.azurewebsites.net/api/user/user/login?format=v1"
ALERTS_URL = "https://prod-aquagen.azurewebsites.net/api/user/alerts"
MARK_READ_URL = "https://prod-aquagen.azurewebsites.net/api/user/notification/updateRead"
USERNAME = ""
PASSWORD = ""
LOGIN_TYPE = "DEFAULT"
TTS_LANG = "en"  # en=English, te=Telugu, hi=Hindi, kn=Kannada, ta=Tamil

# Translations for TTS announcements
TRANSLATIONS = {
    "en": {
        # General
        "alert": "Alert", "of": "of", "at": "at",
        "unread_alert": "Unread alert", "offline_unit": "Offline unit",
        "consumption": "Consumption", "limit": "Limit", "exceeded": "Exceeded",
        # Device status
        "offline": "Device is offline",
        "online": "Device is back online",
        # Tank / stock level
        "filled": "filled",
        "stock_upper": "Tank level upper limit reached",
        "stock_lower": "Tank level lower limit reached",
        "current_stock": "Current Stock",
        "upper_limit": "Upper Limit", "lower_limit": "Lower Limit",
        # Unit / daily threshold
        "daily_limit": "Daily consumption limit reached",
        "daily_limit_90": "90% of daily consumption limit reached",
        "daily_limit_125": "Daily consumption exceeded 125% of limit",
        # Hourly threshold
        "hourly_threshold": "Hourly consumption limit exceeded",
        # Monthly threshold
        "monthly_limit_90": "90% of monthly consumption limit reached",
        "monthly_limit": "Monthly consumption limit reached",
        # Category monthly threshold
        "cat_month_threshold": "Category monthly consumption limit exceeded",
        # Water quality
        "quality_threshold": "Water quality parameter exceeded limit",
        "ph_high": "pH level is high",
        "ph_low": "pH level is low",
        "turbidity_high": "Turbidity level is high",
        "tds_high": "TDS level is high",
        "chlorine_high": "Chlorine level is high",
        "chlorine_low": "Chlorine level is low",
        # Flow rate
        "flow_rate_normal": "Flow rate is back to normal range",
        "flow_rate_above": "Flow rate exceeded upper limit",
        "flow_rate_below": "Flow rate is below lower limit",
        # Stable flow
        "stable_flow": "Stable flow pattern detected",
        # Abnormal usage
        "abnormal": "Abnormal water usage detected",
        # Energy
        "energy_threshold": "Energy parameter exceeded limit",
        "voltage_high": "Voltage is high",
        "voltage_low": "Voltage is low",
        "current_high": "Current is high",
        "power_factor_low": "Power factor is low",
        "energy_daily_limit": "Daily energy consumption limit reached",
        "energy_monthly_limit": "Monthly energy consumption limit reached",
        # Generic / safe range
        "crossed_safe_range": "Crossed the safe range border",
        "exceeded_threshold": "Exceeded threshold limit",
    },
    "te": {
        # General
        "alert": "హెచ్చరిక", "of": "లో", "at": "సమయం",
        "unread_alert": "చదవని హెచ్చరిక", "offline_unit": "ఆఫ్‌లైన్ యూనిట్",
        "consumption": "వినియోగం", "limit": "పరిమితి", "exceeded": "మించింది",
        # Device status
        "offline": "పరికరం ఆఫ్‌లైన్‌లో ఉంది",
        "online": "పరికరం తిరిగి ఆన్‌లైన్‌లో ఉంది",
        # Tank / stock level
        "filled": "నిండింది",
        "stock_upper": "ట్యాంక్ మట్టం పై పరిమితి చేరుకుంది",
        "stock_lower": "ట్యాంక్ మట్టం కింది పరిమితి చేరుకుంది",
        "current_stock": "ప్రస్తుత నిల్వ",
        "upper_limit": "పై పరిమితి", "lower_limit": "కింది పరిమితి",
        # Unit / daily threshold
        "daily_limit": "రోజువారీ వినియోగ పరిమితి చేరుకుంది",
        "daily_limit_90": "రోజువారీ వినియోగ పరిమితిలో 90% చేరుకుంది",
        "daily_limit_125": "రోజువారీ వినియోగ పరిమితి 125% దాటింది",
        # Hourly threshold
        "hourly_threshold": "గంట వినియోగ పరిమితి మించింది",
        # Monthly threshold
        "monthly_limit_90": "నెలవారీ వినియోగ పరిమితిలో 90% చేరుకుంది",
        "monthly_limit": "నెలవారీ వినియోగ పరిమితి చేరుకుంది",
        # Category monthly threshold
        "cat_month_threshold": "వర్గం నెలవారీ వినియోగ పరిమితి మించింది",
        # Water quality
        "quality_threshold": "నీటి నాణ్యత పరామితి పరిమితి మించింది",
        "ph_high": "pH స్థాయి ఎక్కువగా ఉంది",
        "ph_low": "pH స్థాయి తక్కువగా ఉంది",
        "turbidity_high": "నీటి మైలిన స్థాయి ఎక్కువగా ఉంది",
        "tds_high": "TDS స్థాయి ఎక్కువగా ఉంది",
        "chlorine_high": "క్లోరిన్ స్థాయి ఎక్కువగా ఉంది",
        "chlorine_low": "క్లోరిన్ స్థాయి తక్కువగా ఉంది",
        # Flow rate
        "flow_rate_normal": "ప్రవాహ రేటు సాధారణ స్థాయికి వచ్చింది",
        "flow_rate_above": "ప్రవాహ రేటు పై పరిమితి మించింది",
        "flow_rate_below": "ప్రవాహ రేటు కింది పరిమితి కంటే తక్కువగా ఉంది",
        # Stable flow
        "stable_flow": "స్థిర ప్రవాహ నమూనా గుర్తించబడింది",
        # Abnormal usage
        "abnormal": "అసాధారణ నీటి వినియోగం గుర్తించబడింది",
        # Energy
        "energy_threshold": "శక్తి పరామితి పరిమితి మించింది",
        "voltage_high": "వోల్టేజ్ ఎక్కువగా ఉంది",
        "voltage_low": "వోల్టేజ్ తక్కువగా ఉంది",
        "current_high": "విద్యుత్ ప్రవాహం ఎక్కువగా ఉంది",
        "power_factor_low": "పవర్ ఫ్యాక్టర్ తక్కువగా ఉంది",
        "energy_daily_limit": "రోజువారీ విద్యుత్ వినియోగ పరిమితి చేరుకుంది",
        "energy_monthly_limit": "నెలవారీ విద్యుత్ వినియోగ పరిమితి చేరుకుంది",
        # Generic / safe range
        "crossed_safe_range": "సురక్షిత పరిమితి దాటింది",
        "exceeded_threshold": "పరిమితి దాటింది",
    },
    "hi": {
        # General
        "alert": "चेतावनी", "of": "में से", "at": "बजे",
        "unread_alert": "अपठित चेतावनी", "offline_unit": "ऑफलाइन यूनिट",
        "consumption": "खपत", "limit": "सीमा", "exceeded": "पार हो गई",
        # Device status
        "offline": "डिवाइस ऑफलाइन है",
        "online": "डिवाइस वापस ऑनलाइन है",
        # Tank / stock level
        "filled": "भरा हुआ",
        "stock_upper": "टैंक स्तर ऊपरी सीमा पर पहुंच गया",
        "stock_lower": "टैंक स्तर निचली सीमा पर पहुंच गया",
        "current_stock": "वर्तमान स्टॉक",
        "upper_limit": "ऊपरी सीमा", "lower_limit": "निचली सीमा",
        # Unit / daily threshold
        "daily_limit": "दैनिक खपत सीमा पूरी हो गई",
        "daily_limit_90": "दैनिक खपत सीमा का 90% पूरा हो गया",
        "daily_limit_125": "दैनिक खपत सीमा का 125% पार हो गया",
        # Hourly threshold
        "hourly_threshold": "प्रति घंटा खपत सीमा पार हो गई",
        # Monthly threshold
        "monthly_limit_90": "मासिक खपत सीमा का 90% पूरा हो गया",
        "monthly_limit": "मासिक खपत सीमा पूरी हो गई",
        # Category monthly threshold
        "cat_month_threshold": "श्रेणी मासिक खपत सीमा पार हो गई",
        # Water quality
        "quality_threshold": "जल गुणवत्ता मानक सीमा पार हो गई",
        "ph_high": "pH स्तर अधिक है",
        "ph_low": "pH स्तर कम है",
        "turbidity_high": "पानी की गंदगी अधिक है",
        "tds_high": "TDS स्तर अधिक है",
        "chlorine_high": "क्लोरीन स्तर अधिक है",
        "chlorine_low": "क्लोरीन स्तर कम है",
        # Flow rate
        "flow_rate_normal": "प्रवाह दर सामान्य स्थिति में आ गई",
        "flow_rate_above": "प्रवाह दर ऊपरी सीमा से अधिक है",
        "flow_rate_below": "प्रवाह दर निचली सीमा से कम है",
        # Stable flow
        "stable_flow": "स्थिर प्रवाह पैटर्न पाया गया",
        # Abnormal usage
        "abnormal": "असामान्य पानी का उपयोग पाया गया",
        # Energy
        "energy_threshold": "ऊर्जा मानक सीमा पार हो गई",
        "voltage_high": "वोल्टेज अधिक है",
        "voltage_low": "वोल्टेज कम है",
        "current_high": "करंट अधिक है",
        "power_factor_low": "पावर फैक्टर कम है",
        "energy_daily_limit": "दैनिक ऊर्जा खपत सीमा पूरी हो गई",
        "energy_monthly_limit": "मासिक ऊर्जा खपत सीमा पूरी हो गई",
        # Generic / safe range
        "crossed_safe_range": "सुरक्षित सीमा पार हो गई",
        "exceeded_threshold": "सीमा पार हो गई",
    },
    "kn": {
        # General
        "alert": "ಎಚ್ಚರಿಕೆ", "of": "ರಲ್ಲಿ", "at": "ಸಮಯ",
        "unread_alert": "ಓದದ ಎಚ್ಚರಿಕೆ", "offline_unit": "ಆಫ್‌ಲೈನ್ ಘಟಕ",
        "consumption": "ಬಳಕೆ", "limit": "ಮಿತಿ", "exceeded": "ಮೀರಿದೆ",
        # Device status
        "offline": "ಸಾಧನ ಆಫ್‌ಲೈನ್‌ನಲ್ಲಿದೆ",
        "online": "ಸಾಧನ ಮತ್ತೆ ಆನ್‌ಲೈನ್‌ನಲ್ಲಿದೆ",
        # Tank / stock level
        "filled": "ತುಂಬಿದೆ",
        "stock_upper": "ಟ್ಯಾಂಕ್ ಮಟ್ಟ ಮೇಲಿನ ಮಿತಿ ತಲುಪಿದೆ",
        "stock_lower": "ಟ್ಯಾಂಕ್ ಮಟ್ಟ ಕೆಳಗಿನ ಮಿತಿ ತಲುಪಿದೆ",
        "current_stock": "ಪ್ರಸ್ತುತ ದಾಸ್ತಾನು",
        "upper_limit": "ಮೇಲಿನ ಮಿತಿ", "lower_limit": "ಕೆಳಗಿನ ಮಿತಿ",
        # Unit / daily threshold
        "daily_limit": "ದೈನಂದಿನ ಬಳಕೆ ಮಿತಿ ತಲುಪಿದೆ",
        "daily_limit_90": "ದೈನಂದಿನ ಬಳಕೆ ಮಿತಿಯ 90% ತಲುಪಿದೆ",
        "daily_limit_125": "ದೈನಂದಿನ ಬಳಕೆ ಮಿತಿಯ 125% ಮೀರಿದೆ",
        # Hourly threshold
        "hourly_threshold": "ಗಂಟೆಯ ಬಳಕೆ ಮಿತಿ ಮೀರಿದೆ",
        # Monthly threshold
        "monthly_limit_90": "ಮಾಸಿಕ ಬಳಕೆ ಮಿತಿಯ 90% ತಲುಪಿದೆ",
        "monthly_limit": "ಮಾಸಿಕ ಬಳಕೆ ಮಿತಿ ತಲುಪಿದೆ",
        # Category monthly threshold
        "cat_month_threshold": "ವರ್ಗ ಮಾಸಿಕ ಬಳಕೆ ಮಿತಿ ಮೀರಿದೆ",
        # Water quality
        "quality_threshold": "ನೀರಿನ ಗುಣಮಟ್ಟ ನಿಯತಾಂಕ ಮಿತಿ ಮೀರಿದೆ",
        "ph_high": "pH ಮಟ್ಟ ಹೆಚ್ಚಾಗಿದೆ",
        "ph_low": "pH ಮಟ್ಟ ಕಡಿಮೆಯಾಗಿದೆ",
        "turbidity_high": "ನೀರಿನ ಕಲ್ಮಶ ಮಟ್ಟ ಹೆಚ್ಚಾಗಿದೆ",
        "tds_high": "TDS ಮಟ್ಟ ಹೆಚ್ಚಾಗಿದೆ",
        "chlorine_high": "ಕ್ಲೋರಿನ್ ಮಟ್ಟ ಹೆಚ್ಚಾಗಿದೆ",
        "chlorine_low": "ಕ್ಲೋರಿನ್ ಮಟ್ಟ ಕಡಿಮೆಯಾಗಿದೆ",
        # Flow rate
        "flow_rate_normal": "ಹರಿವಿನ ಪ್ರಮಾಣ ಸಾಮಾನ್ಯ ಸ್ಥಿತಿಗೆ ಮರಳಿದೆ",
        "flow_rate_above": "ಹರಿವಿನ ಪ್ರಮಾಣ ಮೇಲಿನ ಮಿತಿ ಮೀರಿದೆ",
        "flow_rate_below": "ಹರಿವಿನ ಪ್ರಮಾಣ ಕೆಳಗಿನ ಮಿತಿಗಿಂತ ಕಡಿಮೆಯಾಗಿದೆ",
        # Stable flow
        "stable_flow": "ಸ್ಥಿರ ಹರಿವಿನ ಮಾದರಿ ಪತ್ತೆಯಾಗಿದೆ",
        # Abnormal usage
        "abnormal": "ಅಸಹಜ ನೀರಿನ ಬಳಕೆ ಪತ್ತೆಯಾಗಿದೆ",
        # Energy
        "energy_threshold": "ಶಕ್ತಿ ನಿಯತಾಂಕ ಮಿತಿ ಮೀರಿದೆ",
        "voltage_high": "ವೋಲ್ಟೇಜ್ ಹೆಚ್ಚಾಗಿದೆ",
        "voltage_low": "ವೋಲ್ಟೇಜ್ ಕಡಿಮೆಯಾಗಿದೆ",
        "current_high": "ವಿದ್ಯುತ್ ಪ್ರವಾಹ ಹೆಚ್ಚಾಗಿದೆ",
        "power_factor_low": "ಪವರ್ ಫ್ಯಾಕ್ಟರ್ ಕಡಿಮೆಯಾಗಿದೆ",
        "energy_daily_limit": "ದೈನಂದಿನ ವಿದ್ಯುತ್ ಬಳಕೆ ಮಿತಿ ತಲುಪಿದೆ",
        "energy_monthly_limit": "ಮಾಸಿಕ ವಿದ್ಯುತ್ ಬಳಕೆ ಮಿತಿ ತಲುಪಿದೆ",
        # Generic / safe range
        "crossed_safe_range": "ಸುರಕ್ಷಿತ ಮಿತಿ ದಾಟಿದೆ",
        "exceeded_threshold": "ಮಿತಿ ದಾಟಿದೆ",
    },
    "ml": {
        # General
        "alert": "മുന്നറിയിപ്പ്", "of": "ൽ", "at": "സമയം",
        "unread_alert": "വായിക്കാത്ത മുന്നറിയിപ്പ്", "offline_unit": "ഓഫ്‌ലൈൻ യൂണിറ്റ്",
        "consumption": "ഉപഭോഗം", "limit": "പരിധി", "exceeded": "കടന്നു",
        # Device status
        "offline": "ഉപകരണം ഓഫ്‌ലൈനിലാണ്",
        "online": "ഉപകരണം വീണ്ടും ഓൺലൈനിലാണ്",
        # Tank / stock level
        "filled": "നിറഞ്ഞു",
        "stock_upper": "ടാങ്ക് നിരപ്പ് ഉയർന്ന പരിധി എത്തി",
        "stock_lower": "ടാങ്ക് നിരപ്പ് താഴ്ന്ന പരിധി എത്തി",
        "current_stock": "നിലവിലെ സ്റ്റോക്ക്",
        "upper_limit": "ഉയർന്ന പരിധി", "lower_limit": "താഴ്ന്ന പരിധി",
        # Unit / daily threshold
        "daily_limit": "ദൈനംദിന ഉപഭോഗ പരിധി എത്തി",
        "daily_limit_90": "ദൈനംദിന ഉപഭോഗ പരിധിയുടെ 90% എത്തി",
        "daily_limit_125": "ദൈനംദിന ഉപഭോഗ പരിധിയുടെ 125% കടന്നു",
        # Hourly threshold
        "hourly_threshold": "മണിക്കൂർ ഉപഭോഗ പരിധി കടന്നു",
        # Monthly threshold
        "monthly_limit_90": "മാസ ഉപഭോഗ പരിധിയുടെ 90% എത്തി",
        "monthly_limit": "മാസ ഉപഭോഗ പരിധി എത്തി",
        # Category monthly threshold
        "cat_month_threshold": "വിഭാഗ മാസ ഉപഭോഗ പരിധി കടന്നു",
        # Water quality
        "quality_threshold": "ജല ഗുണനിലവാര നിർണ്ണായക പരിധി കടന്നു",
        "ph_high": "pH നില ഉയർന്നിരിക്കുന്നു",
        "ph_low": "pH നില താഴ്ന്നിരിക്കുന്നു",
        "turbidity_high": "ജലത്തിന്റെ മലിനത ഉയർന്നിരിക്കുന്നു",
        "tds_high": "TDS നില ഉയർന്നിരിക്കുന്നു",
        "chlorine_high": "ക്ലോറിൻ നില ഉയർന്നിരിക്കുന്നു",
        "chlorine_low": "ക്ലോറിൻ നില താഴ്ന്നിരിക്കുന്നു",
        # Flow rate
        "flow_rate_normal": "ഒഴുക്ക് നിരക്ക് സാധാരണ നിലയിലേക്ക് മടങ്ങി",
        "flow_rate_above": "ഒഴുക്ക് നിരക്ക് ഉയർന്ന പരിധി കടന്നു",
        "flow_rate_below": "ഒഴുക്ക് നിരക്ക് താഴ്ന്ന പരിധിക്ക് കീഴെ",
        # Stable flow
        "stable_flow": "സ്ഥിരമായ ഒഴുക്ക് ക്രമം കണ്ടെത്തി",
        # Abnormal usage
        "abnormal": "അസാധാരണ ജല ഉപയോഗം കണ്ടെത്തി",
        # Energy
        "energy_threshold": "ഊർജ്ജ നിർണ്ണായക പരിധി കടന്നു",
        "voltage_high": "വോൾട്ടേജ് ഉയർന്നിരിക്കുന്നു",
        "voltage_low": "വോൾട്ടേജ് താഴ്ന്നിരിക്കുന്നു",
        "current_high": "വൈദ്യുത പ്രവാഹം ഉയർന്നിരിക്കുന്നു",
        "power_factor_low": "പവർ ഫാക്ടർ താഴ്ന്നിരിക്കുന്നു",
        "energy_daily_limit": "ദൈനംദിന വൈദ്യുത ഉപഭോഗ പരിധി എത്തി",
        "energy_monthly_limit": "മാസ വൈദ്യുത ഉപഭോഗ പരിധി എത്തി",
        # Generic / safe range
        "crossed_safe_range": "സുരക്ഷിത പരിധി കടന്നു",
        "exceeded_threshold": "പരിധി കടന്നു",
    },
    "ta": {
        # General
        "alert": "எச்சரிக்கை", "of": "இல்", "at": "நேரம்",
        "unread_alert": "படிக்காத எச்சரிக்கை", "offline_unit": "ஆஃப்லைன் அலகு",
        "consumption": "நுகர்வு", "limit": "வரம்பு", "exceeded": "தாண்டியது",
        # Device status
        "offline": "சாதனம் ஆஃப்லைனில் உள்ளது",
        "online": "சாதனம் மீண்டும் ஆன்லைனில் உள்ளது",
        # Tank / stock level
        "filled": "நிரம்பியது",
        "stock_upper": "தொட்டி மட்டம் மேல் வரம்பை எட்டியது",
        "stock_lower": "தொட்டி மட்டம் கீழ் வரம்பை எட்டியது",
        "current_stock": "தற்போதைய இருப்பு",
        "upper_limit": "மேல் வரம்பு", "lower_limit": "கீழ் வரம்பு",
        # Unit / daily threshold
        "daily_limit": "தினசரி நுகர்வு வரம்பு எட்டியது",
        "daily_limit_90": "தினசரி நுகர்வு வரம்பின் 90% எட்டியது",
        "daily_limit_125": "தினசரி நுகர்வு வரம்பின் 125% தாண்டியது",
        # Hourly threshold
        "hourly_threshold": "மணிநேர நுகர்வு வரம்பு தாண்டியது",
        # Monthly threshold
        "monthly_limit_90": "மாதாந்திர நுகர்வு வரம்பின் 90% எட்டியது",
        "monthly_limit": "மாதாந்திர நுகர்வு வரம்பு எட்டியது",
        # Category monthly threshold
        "cat_month_threshold": "பிரிவு மாதாந்திர நுகர்வு வரம்பு தாண்டியது",
        # Water quality
        "quality_threshold": "நீர் தர அளவுரு வரம்பு தாண்டியது",
        "ph_high": "pH அளவு அதிகமாக உள்ளது",
        "ph_low": "pH அளவு குறைவாக உள்ளது",
        "turbidity_high": "நீரின் கலக்கம் அதிகமாக உள்ளது",
        "tds_high": "TDS அளவு அதிகமாக உள்ளது",
        "chlorine_high": "குளோரின் அளவு அதிகமாக உள்ளது",
        "chlorine_low": "குளோரின் அளவு குறைவாக உள்ளது",
        # Flow rate
        "flow_rate_normal": "ஓட்ட விகிதம் இயல்பு நிலைக்கு திரும்பியது",
        "flow_rate_above": "ஓட்ட விகிதம் மேல் வரம்பை தாண்டியது",
        "flow_rate_below": "ஓட்ட விகிதம் கீழ் வரம்பிற்கு கீழே உள்ளது",
        # Stable flow
        "stable_flow": "நிலையான ஓட்ட வடிவம் கண்டறியப்பட்டது",
        # Abnormal usage
        "abnormal": "அசாதாரண நீர் பயன்பாடு கண்டறியப்பட்டது",
        # Energy
        "energy_threshold": "ஆற்றல் அளவுரு வரம்பு தாண்டியது",
        "voltage_high": "மின்னழுத்தம் அதிகமாக உள்ளது",
        "voltage_low": "மின்னழுத்தம் குறைவாக உள்ளது",
        "current_high": "மின்னோட்டம் அதிகமாக உள்ளது",
        "power_factor_low": "திறன் காரணி குறைவாக உள்ளது",
        "energy_daily_limit": "தினசரி மின் நுகர்வு வரம்பு எட்டியது",
        "energy_monthly_limit": "மாதாந்திர மின் நுகர்வு வரம்பு எட்டியது",
        # Generic / safe range
        "crossed_safe_range": "பாதுகாப்பான வரம்பை தாண்டியது",
        "exceeded_threshold": "வரம்பு தாண்டியது",
    },
}


def translate_alert_text(title, body, status, lang):
    """Translate alert text to local language, keep location name in English."""
    body = str(body)
    status = str(status)
    t = TRANSLATIONS.get(lang, TRANSLATIONS["en"])

    def _time_suffix(text):
        """Extract time portion after 'at' and return formatted suffix."""
        if " at " in text.lower():
            idx = text.lower().rfind(" at ")
            time_part = text[idx + 4:].strip()
            return " " + t["at"] + " " + time_part if time_part else ""
        return ""

    def _translate_quality_status(s):
        """Return translated quality alert from status string."""
        sl = s.lower()
        if "ph" in sl and ("high" in sl or "above" in sl or "exceed" in sl):
            return t["ph_high"]
        if "ph" in sl and ("low" in sl or "below" in sl):
            return t["ph_low"]
        if "turbidity" in sl and ("high" in sl or "above" in sl or "exceed" in sl):
            return t["turbidity_high"]
        if "tds" in sl and ("high" in sl or "above" in sl or "exceed" in sl):
            return t["tds_high"]
        if "chlorine" in sl and ("high" in sl or "above" in sl or "exceed" in sl):
            return t["chlorine_high"]
        if "chlorine" in sl and ("low" in sl or "below" in sl):
            return t["chlorine_low"]
        return t["quality_threshold"]

    def _translate_energy_status(s):
        """Return translated energy alert from status string."""
        sl = s.lower()
        if "voltage" in sl and ("high" in sl or "above" in sl or "exceed" in sl):
            return t["voltage_high"]
        if "voltage" in sl and ("low" in sl or "below" in sl):
            return t["voltage_low"]
        if "current" in sl and ("high" in sl or "above" in sl or "exceed" in sl):
            return t["current_high"]
        if "power factor" in sl and ("low" in sl or "below" in sl):
            return t["power_factor_low"]
        return t["energy_threshold"]

    # ── Body translation ─────────────────────────────────────────────────────
    translated_body = body
    bl = body.lower()

    if "filled" in bl:
        parts = body.split("%")
        if len(parts) > 1:
            translated_body = parts[0] + "% " + t["filled"]
        else:
            translated_body = body.replace("filled", t["filled"])

    elif "125%" in bl and ("daily" in bl or "limit" in bl):
        translated_body = t["daily_limit_125"]
    elif "90%" in bl and ("daily" in bl or "limit" in bl):
        translated_body = t["daily_limit_90"]
    elif ("daily" in bl and "limit" in bl) or "daily consumption limit" in bl:
        translated_body = t["daily_limit"]

    elif "hourly" in bl and ("limit" in bl or "threshold" in bl or "exceeded" in bl):
        translated_body = t["hourly_threshold"]

    elif "90%" in bl and "monthly" in bl:
        translated_body = t["monthly_limit_90"]
    elif "monthly" in bl and ("limit" in bl or "threshold" in bl or "consumption" in bl):
        translated_body = t["monthly_limit"]

    elif "category" in bl and "monthly" in bl:
        translated_body = t["cat_month_threshold"]

    elif "upper limit" in bl or "upper limit reached" in bl:
        translated_body = t["stock_upper"]
    elif "lower limit" in bl or "lower limit reached" in bl:
        translated_body = t["stock_lower"]

    elif "ph" in bl or "turbidity" in bl or "tds" in bl or "chlorine" in bl or "quality" in bl:
        translated_body = _translate_quality_status(body)

    elif "back" in bl and "range" in bl and "flow" in bl:
        translated_body = t["flow_rate_normal"]
    elif "flow" in bl and ("above" in bl or "exceed" in bl or "upper" in bl):
        translated_body = t["flow_rate_above"]
    elif "flow" in bl and ("below" in bl or "lower" in bl):
        translated_body = t["flow_rate_below"]
    elif "stable flow" in bl:
        translated_body = t["stable_flow"]

    elif "abnormal" in bl:
        translated_body = t["abnormal"]

    elif bl.strip() == "offline":
        translated_body = t["offline"]
    elif bl.strip() == "online":
        translated_body = t["online"]
    elif "offline" in bl:
        translated_body = t["offline"]
    elif "online" in bl:
        translated_body = t["online"]

    elif "voltage" in bl or "current" in bl or "power factor" in bl:
        translated_body = _translate_energy_status(body)
    elif "energy" in bl and ("daily" in bl or "kwh" in bl):
        translated_body = t["energy_daily_limit"]
    elif "energy" in bl and "monthly" in bl:
        translated_body = t["energy_monthly_limit"]
    elif "energy" in bl and ("limit" in bl or "threshold" in bl):
        translated_body = t["energy_threshold"]

    elif "crossed" in bl and "safe" in bl:
        translated_body = t["crossed_safe_range"]
    elif "safe range" in bl:
        translated_body = t["crossed_safe_range"]
    elif "exceeded" in bl and "threshold" in bl:
        translated_body = t["exceeded_threshold"]

    # ── Status translation ────────────────────────────────────────────────────
    translated_status = status
    sl = status.lower()

    if "upper limit reached" in sl or "upper limit" in sl:
        translated_status = t["stock_upper"] + _time_suffix(status)
    elif "lower limit reached" in sl or "lower limit" in sl:
        translated_status = t["stock_lower"] + _time_suffix(status)

    elif "125%" in sl and ("daily" in sl or "limit" in sl):
        translated_status = t["daily_limit_125"] + _time_suffix(status)
    elif "90%" in sl and ("daily" in sl or "limit" in sl):
        translated_status = t["daily_limit_90"] + _time_suffix(status)
    elif "daily consumption" in sl or ("daily" in sl and "limit" in sl):
        translated_status = t["daily_limit"] + _time_suffix(status)

    elif "hourly" in sl and ("limit" in sl or "exceeded" in sl or "threshold" in sl):
        translated_status = t["hourly_threshold"] + _time_suffix(status)

    elif "90%" in sl and "monthly" in sl:
        translated_status = t["monthly_limit_90"] + _time_suffix(status)
    elif "monthly" in sl and ("limit" in sl or "consumption" in sl):
        translated_status = t["monthly_limit"] + _time_suffix(status)

    elif "category" in sl and "monthly" in sl:
        translated_status = t["cat_month_threshold"] + _time_suffix(status)

    elif "ph" in sl or "turbidity" in sl or "tds" in sl or "chlorine" in sl or "quality" in sl:
        translated_status = _translate_quality_status(status)

    elif "back" in sl and "range" in sl and "flow" in sl:
        translated_status = t["flow_rate_normal"]
    elif "flow" in sl and ("above" in sl or "exceed" in sl or "upper" in sl):
        translated_status = t["flow_rate_above"]
    elif "flow" in sl and ("below" in sl or "lower" in sl):
        translated_status = t["flow_rate_below"]
    elif "stable flow" in sl:
        translated_status = t["stable_flow"]

    elif "abnormal" in sl:
        translated_status = t["abnormal"]

    elif "device is offline" in sl or sl.strip() == "offline":
        translated_status = t["offline"]
    elif "device is" in sl and "online" in sl:
        translated_status = t["online"]
    elif "offline" in sl:
        translated_status = t["offline"]
    elif "online" in sl:
        translated_status = t["online"]

    elif "voltage" in sl or ("current" in sl and "high" in sl) or "power factor" in sl:
        translated_status = _translate_energy_status(status)
    elif "energy" in sl and ("daily" in sl or "kwh" in sl) and "monthly" not in sl:
        translated_status = t["energy_daily_limit"] + _time_suffix(status)
    elif "energy" in sl and "monthly" in sl:
        translated_status = t["energy_monthly_limit"] + _time_suffix(status)
    elif "energy" in sl and ("limit" in sl or "threshold" in sl or "exceed" in sl):
        translated_status = t["energy_threshold"] + _time_suffix(status)

    elif "crossed" in sl and "safe" in sl:
        translated_status = t["crossed_safe_range"]
    elif "safe range" in sl:
        translated_status = t["crossed_safe_range"]
    elif "exceeded" in sl and "threshold" in sl:
        translated_status = t["exceeded_threshold"]

    # Title stays in English (location name)
    return title, translated_body, translated_status


LOGGED_IN = False
CREDS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "user_session.json")
ADMIN_CONFIG = os.path.join(os.path.dirname(os.path.abspath(__file__)), "admin_config.json")
ADMIN_USER = "admin"
ADMIN_PASS = "admin"
REFRESH_INTERVAL = 120  # seconds (2 minutes)
OFFLINE_ANNOUNCE_INTERVAL = 3600  # 1 hour auto-announce offline  # seconds (2 minutes)
TOKEN_REFRESH = 13800  # refresh token every 3hr 50min (10 min before 4hr expiry)
AUTO_MARK_READ = True  # Auto mark alerts as read when displayed
ANNOUNCED_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "announced_alerts.json")

# ==================== GLOBALS ====================
token = ""
token_time = 0
alerts_data = {}
fetch_lock = threading.Lock()
FETCH_LOCK_TIMEOUT = 20  # seconds
announced_ids = set()  # Track announced alert IDs to avoid repeats
_announce_stop = False  # Flag to stop announcing
_auto_announcing = False  # Prevent overlapping auto-announce
_refresh_queued = False  # Queue refresh if announce is running
# No lock needed - _announce_stop handles cancellation
_audio_cache = {}  # Pre-generated audio {alert_id: wav_path}
_cache_lock = threading.Lock()


def _start_announcing():
    """Cancel any previous announcement before starting new one."""
    global _announce_stop
    _announce_stop = True
    subprocess.run(["killall", "aplay"], capture_output=True)
    time.sleep(0.3)
    _announce_stop = False
    return True

def _stop_announcing():
    pass  # No lock to release

def set_api_credentials(user, passwd, lt):
    global USERNAME, PASSWORD, LOGIN_TYPE, token, token_time
    USERNAME = user
    PASSWORD = passwd
    LOGIN_TYPE = lt
    token = ""
    token_time = 0

def precache_audio(alerts):
    """Pre-generate gTTS audio for all alerts in background."""
    global _audio_cache
    # Clean old cache files older than 1 day
    try:
        subprocess.run(["find", "/tmp", "-name", "cache_*.mp3", "-mmin", "+1440", "-delete"], capture_output=True, timeout=5)
        subprocess.run(["find", "/tmp", "-name", "cache_*.wav", "-mmin", "+1440", "-delete"], capture_output=True, timeout=5)
    except: pass
    for alert in alerts:
        aid = alert.get("id", "")
        if aid in _audio_cache:
            continue
        title = alert.get("title", "")
        body = alert.get("body", "")
        desc = alert.get("description", {})
        status = desc.get("status", "")
        _, t_body_s, t_status_s = translate_alert_text(title, body, status, TTS_LANG)
        text = title + ". " + t_body_s + ". " + t_status_s
        try:
            mp3 = f"/tmp/cache_{hash(aid) & 0xFFFFFFFF}.mp3"
            wav = f"/tmp/cache_{hash(aid) & 0xFFFFFFFF}.wav"
            if _tts_generate(text, TTS_LANG, mp3, wav):
                with _cache_lock:
                    _audio_cache[aid] = wav
                print(f"[{datetime.now().strftime('%H:%M:%S')}] Cached audio: {title[:30]}")
        except Exception as e:
            print(f"Audio cache error: {e}")


# ==================== API ====================
def save_session():
    try:
        with open(CREDS_FILE, "w") as f:
            json.dump({"username": USERNAME, "password": PASSWORD}, f)
    except: pass

def load_admin_config():
    global USERNAME, PASSWORD, LOGIN_TYPE, TTS_LANG
    try:
        if os.path.exists(ADMIN_CONFIG):
            with open(ADMIN_CONFIG) as f:
                d = json.load(f)
                if d.get("api_username") and d.get("api_password"):
                    USERNAME = d["api_username"]
                    PASSWORD = d["api_password"]
                    LOGIN_TYPE = d.get("login_type", "DEFAULT")
                    TTS_LANG = d.get("tts_lang", "en")
                    return True
    except: pass
    return False

def save_admin_config(api_user, api_pass, login_type="DEFAULT", tts_lang="en"):
    try:
        with open(ADMIN_CONFIG, "w") as f:
            json.dump({"api_username": api_user, "api_password": api_pass, "login_type": login_type, "tts_lang": tts_lang}, f)
        return True
    except: return False

def load_session():
    global USERNAME, PASSWORD, LOGGED_IN
    try:
        if os.path.exists(CREDS_FILE):
            with open(CREDS_FILE) as f:
                d = json.load(f)
                USERNAME = d.get("username", "")
                PASSWORD = d.get("password", "")
                if USERNAME and PASSWORD:
                    LOGGED_IN = True
                    return True
    except: pass
    return False

def get_token():
    global token, token_time
    try:
        resp = requests.get(AUTH_URL, headers={
            "accept": "application/json",
            "username": USERNAME,
            "password": PASSWORD,
            "LoginType": LOGIN_TYPE
        }, timeout=30)
        if resp.status_code == 200:
            data = resp.json()
            t = data.get("token") or data.get("data", {}).get("token", "")
            if t:
                token = t.replace("Bearer ", "")
                token_time = time.time()
                print(f"[{now()}] Token refreshed")
                return True
        print(f"[{now()}] Token failed: {resp.status_code}")
        return False
    except Exception as e:
        print(f"[{now()}] Token error: {e}")
        return False


def fetch_alerts():
    global alerts_data, token, token_time
    if not fetch_lock.acquire(timeout=FETCH_LOCK_TIMEOUT):
        print(f"[{now()}] fetch_lock timeout - skipping fetch")
        return None
    try:
        # Refresh token if needed
        if not token or (time.time() - token_time) > TOKEN_REFRESH:
            if not get_token():
                return None

        for attempt in range(2):
            try:
                today = datetime.now().strftime("%d/%m/%Y")
                resp = requests.get(
                    f"{ALERTS_URL}?date={today}&type=daily",
                    headers={
                        "accept": "application/json",
                        "authorization": f"Bearer {token}"
                    },
                    timeout=15
                )
                if resp.status_code == 200:
                    alerts_data = resp.json()
                    print(f"[{now()}] Alerts fetched: {alerts_data.get('generalAlerts', {}).get('meta', {}).get('total', 0)} total")
                    return alerts_data
                elif resp.status_code in (401, 403, 422):
                    # Token expired (4hr expiry) — refresh and retry
                    print(f"[{now()}] Token expired (HTTP {resp.status_code}), refreshing... (attempt {attempt+1})")
                    token = ""
                    token_time = 0
                    if get_token():
                        continue  # retry with new token
                    else:
                        break
                else:
                    print(f"[{now()}] Alerts failed: {resp.status_code}")
                    break
            except Exception as e:
                print(f"[{now()}] Alerts error: {e}")
                break
        return None
    finally:
        fetch_lock.release()


def now():
    return datetime.now().strftime("%H:%M:%S")


def _tts_generate(text, lang, mp3_path, wav_path):
    """Generate TTS audio with fallback to espeak if gTTS (internet) fails."""
    try:
        from gtts import gTTS
        tts = gTTS(text=text, lang=lang) if lang != "en" else gTTS(text=text, lang="en", tld="co.in")
        tts.save(mp3_path)
        subprocess.run(["ffmpeg", "-y", "-i", mp3_path, "-ar", "44100", "-ac", "1",
                        "-filter:a", "volume=1.5,highpass=f=100,lowpass=f=8000",
                        wav_path], capture_output=True, timeout=30)
        return True
    except Exception as e:
        print(f"[{now()}] gTTS failed ({e}), falling back to espeak")
        try:
            subprocess.run(["espeak", "-w", wav_path, "-s", "140", text[:500]],
                          capture_output=True, timeout=15)
            return True
        except Exception as e2:
            print(f"[{now()}] espeak also failed: {e2}")
            return False


def mark_alerts_as_read(alerts_list):
    """Mark a list of alerts as read via the API."""
    global token, token_time
    if not alerts_list or not token:
        return

    unread = [a for a in alerts_list if not a.get("isRead", True)]
    if not unread:
        return

    notifications = []
    for a in unread:
        notifications.append({
            "id": a.get("id", ""),
            "date": a.get("date_key", a.get("date", "")),
            "type": a.get("type", "")
        })

    if not notifications:
        return

    try:
        resp = requests.patch(
            MARK_READ_URL,
            headers={
                "accept": "application/json",
                "authorization": f"Bearer {token}",
                "content-type": "application/json"
            },
            json={"notifications": notifications},
            timeout=10
        )
        if resp.status_code in (200, 201, 204):
            print(f"[{now()}] Marked {len(notifications)} alerts as read")
            # Update local state
            for a in unread:
                a["isRead"] = True
        elif resp.status_code in (401, 403):
            print(f"[{now()}] Token expired during mark-read, will refresh next cycle")
            token = ""
            token_time = 0
        else:
            print(f"[{now()}] Mark-read failed: {resp.status_code}")
    except Exception as e:
        print(f"[{now()}] Mark-read error: {e}")


def load_announced():
    """Load previously announced alert IDs from file."""
    global announced_ids
    try:
        if os.path.exists(ANNOUNCED_FILE):
            with open(ANNOUNCED_FILE, "r") as f:
                data = json.load(f)
                # Only keep today's IDs
                today = datetime.now().strftime("%Y-%m-%d")
                announced_ids = set(data.get(today, []))
    except Exception:
        announced_ids = set()


def save_announced():
    """Save announced alert IDs to file."""
    try:
        today = datetime.now().strftime("%Y-%m-%d")
        with open(ANNOUNCED_FILE, "w") as f:
            json.dump({today: list(announced_ids)}, f)
    except Exception:
        pass


def mark_as_announced(alert_id):
    """Mark an alert as announced (for TTS)."""
    announced_ids.add(alert_id)
    save_announced()


def is_announced(alert_id):
    """Check if alert was already announced."""
    return alert_id in announced_ids


def get_unannounced_alerts(alerts_list):
    """Get alerts that haven't been announced yet (for TTS use)."""
    return [a for a in alerts_list if not is_announced(a.get("id", ""))]


def announce_and_mark_read(alert):
    """
    Call this after TTS announces an alert.
    1. Marks alert as announced (won't repeat in TTS)
    2. Marks alert as read via API
    """
    alert_id = alert.get("id", "")
    if alert_id:
        mark_as_announced(alert_id)
        mark_alerts_as_read([alert])
        print(f"[{now()}] Alert announced & marked read: {alert.get('title', '')} ({alert_id})")


# ==================== GTK DISPLAY ====================
COLORS = {
    "high": {"bg": "#fee2e2", "border": "#ef4444", "text": "#991b1b", "badge": "#dc2626"},
    "medium": {"bg": "#fef3c7", "border": "#f59e0b", "text": "#92400e", "badge": "#d97706"},
    "low": {"bg": "#dbeafe", "border": "#3b82f6", "text": "#1e3a5a", "badge": "#2563eb"},
    "info": {"bg": "#f0fdf4", "border": "#22c55e", "text": "#14532d", "badge": "#16a34a"},
}

CSS = """
window { background-color: #ffffff; }

/* Optimized for 1024x600 7-inch display */
.header-bar {
    background: linear-gradient(to right, #1e3a5a, #1e40af);
    padding: 20px 14px;
    border-bottom: 2px solid #3b82f6;
}
.header-title {
    color: white;
    font-size: 24px;
    font-weight: bold;
}
.header-sub {
    color: #93c5fd;
    font-size: 24px;
}

.stats-bar {
    background-color: #f0f4ff;
    padding: 10px 12px;
    border-bottom: 1px solid #e0e4ea;
}
.stat-box {
    background-color: #ffffff;
    border-radius: 7px;
    padding: 8px 10px;
    margin: 2px 4px;
    border: 1px solid #d0d5dd;
}
.stat-num {
    color: #1565c0;
    font-size: 24px;
    font-weight: bold;
}
.stat-label {
    color: #555555;
    font-size: 24px;
}
.stat-num-unread { color: #f87171; }
.stat-num-read { color: #4ade80; }
.stat-num-total { color: #60a5fa; }

.alerts-scroll {
    background-color: #ffffff;
}

.alert-card {
    border-radius: 9px;
    padding: 12px;
    margin: 5px 8px;
    border-left-width: 4px;
    border-left-style: solid;
}
.alert-title {
    font-size: 24px;
    font-weight: bold;
}
.alert-body {
    font-size: 24px;
    margin-top: 2px;
}
.alert-time {
    font-size: 24px;
    color: #64748b;
    margin-top: 2px;
}
.alert-detail {
    font-size: 24px;
    margin-top: 3px;
    padding: 4px 6px;
    border-radius: 4px;
    background-color: rgba(0,0,0,0.05);
}
.alert-badge {
    font-size: 24px;
    font-weight: bold;
    padding: 2px 8px;
    border-radius: 9px;
    color: white;
}
.alert-unread { font-weight: bold; }

.unread-dot {
    color: #ef4444;
    font-size: 24px;
}
.read-check {
    color: #22c55e;
    font-size: 24px;
}

.alert-actions {
    margin-top: 6px;
    padding-top: 6px;
    border-top: 1px solid rgba(0,0,0,0.08);
}
.btn-mark-read {
    background: #22c55e;
    color: white;
    border: none;
    border-radius: 6px;
    font-size: 24px;
    font-weight: bold;
    padding: 6px 14px;
    min-height: 31px;
}
.btn-mark-read:hover { background: #16a34a; }
.btn-announce {
    background: #3b82f6;
    color: white;
    border: none;
    border-radius: 6px;
    font-size: 24px;
    font-weight: bold;
    padding: 6px 14px;
    min-height: 31px;
}
.btn-announce:hover { background: #2563eb; }
.btn-done {
    background: #94a3b8;
    color: white;
    border: none;
    border-radius: 6px;
    font-size: 24px;
    padding: 4px 12px;
    min-height: 29px;
}
.btn-done:hover { background: #64748b; }

.alert-expander {
    color: #64748b;
    font-size: 24px;
    padding-top: 4px;
}
.alert-expander title {
    color: #64748b;
    font-size: 24px;
}

.offline-card {
    background-color: #fff5f5;
    border-radius: 11px;
    padding: 11px;
    margin: 4px 8px;
    border-left: 4px solid #ef4444;
}
.offline-title {
    color: #c62828;
    font-size: 24px;
    font-weight: bold;
}
.offline-body {
    color: #555555;
    font-size: 24px;
}

.section-header {
    color: #333333;
    font-size: 24px;
    font-weight: bold;
    padding: 8px 12px 4px;
}

.refresh-bar {
    background-color: #1565c0;
    padding: 8px 14px;
    border-top: 1px solid #1255a0;
}
.refresh-text {
    color: #ffffff;
    font-size: 24px;
}

.announce-bar {
    background-color: #1e3a5a;
    padding: 9px 14px;
    border-top: 1px solid #3b82f6;
}
.announce-text {
    color: #60a5fa;
    font-size: 24px;
    font-weight: bold;
    font-family: monospace;
}

.announce-overlay {
    background-color: rgba(0, 0, 0, 0.88);
    border-radius: 20px;
    padding: 33px 24px;
    border: 1px solid rgba(59, 130, 246, 0.3);
}
.announce-overlay-icon {
    color: #60a5fa;
    font-size: 24px;
}
.announce-overlay-text {
    color: #ffffff;
    font-size: 24px;
    font-family: monospace;
    font-weight: bold;
    min-height: 66px;
}
.announce-overlay-title {
    color: #94a3b8;
    font-size: 24px;
    font-weight: bold;
    letter-spacing: 1px;
}


.header-lang {
    background: #0d2b5e;
    color: #93c5fd;
    border: 1px solid #1e40af;
    border-radius: 6px;
    padding: 2px 6px;
    font-size: 24px;
    min-height: 24px;
}

.refresh-btn {
    background: rgba(255,255,255,0.12);
    border: 1px solid rgba(255,255,255,0.2);
    border-radius: 15px;
    padding: 2px;
    min-width: 36px;
    min-height: 36px;
}
.refresh-btn:hover {
    background: rgba(255,255,255,0.25);
}
.refresh-btn:active {
    background: rgba(255,255,255,0.35);
}

.header-clock {
    color: white;
    font-size: 24px;
    font-weight: bold;
}
.header-date {
    color: #93c5fd;
    font-size: 24px;
}

.no-alerts {
    color: #2e7d32;
    font-size: 24px;
    font-weight: bold;
    padding: 44px;
}

.wifi-btn, .speaker-btn {
    background: rgba(255,255,255,0.12);
    border: none;
    border-radius: 4px;
    padding: 2px 6px;
    min-width: 28px;
    min-height: 28px;
    color: #ffffff;
}
.wifi-btn:hover, .speaker-btn:hover {
    background: rgba(255,255,255,0.25);
}
.wifi-popup, .volume-popup {
    background-color: #1e3a5a;
    border: 1px solid #3b82f6;
    border-radius: 8px;
    padding: 10px 14px;
}
.wifi-ssid {
    color: #ffffff;
    font-size: 24px;
    font-weight: bold;
}
.wifi-signal {
    color: #93c5fd;
    font-size: 18px;
}
.wifi-net-row {
    background: rgba(255,255,255,0.06);
    border-radius: 6px;
    padding: 6px 10px;
    margin: 2px 0;
}
.wifi-net-row:hover {
    background: rgba(255,255,255,0.15);
}
.wifi-net-name {
    color: #ffffff;
    font-size: 18px;
    font-weight: bold;
}
.wifi-net-signal {
    color: #93c5fd;
    font-size: 16px;
}
.wifi-net-connected {
    color: #4ade80;
    font-size: 16px;
    font-weight: bold;
}
.wifi-scan-btn {
    background: #1e40af;
    color: white;
    border: 1px solid #3b82f6;
    border-radius: 6px;
    padding: 4px 12px;
    font-size: 16px;
}
.wifi-scan-btn:hover {
    background: #2563eb;
}
.wifi-connect-btn {
    background: #16a34a;
    color: white;
    border: none;
    border-radius: 6px;
    padding: 4px 12px;
    font-size: 16px;
}
.wifi-connect-btn:hover {
    background: #22c55e;
}
.wifi-disconnect-btn {
    background: #dc2626;
    color: white;
    border: none;
    border-radius: 6px;
    padding: 4px 10px;
    font-size: 16px;
}
.wifi-disconnect-btn:hover {
    background: #ef4444;
}
.wifi-status-label {
    color: #fbbf24;
    font-size: 16px;
}
.wifi-pass-entry {
    background: rgba(255,255,255,0.1);
    color: white;
    border: 1px solid #3b82f6;
    border-radius: 4px;
    padding: 4px 8px;
    font-size: 18px;
}
.volume-label {
    color: #93c5fd;
    font-size: 18px;
}
"""


class LoginWindow(Gtk.Window):
    def __init__(self):
        super().__init__(title="AquaBox Login")
        self.set_default_size(1024, 600)
        self.fullscreen()
        self.set_app_paintable(True)
        self._kb_visible = False
        self._wave_offset = 0
        self._pulse = 0
        self._drops = []
        self._ripples = []
        self._last_ripple = 0
        for _ in range(30):
            self._drops.append({
                "x": _random.uniform(0, 800), "y": _random.uniform(-50, 480),
                "r": _random.uniform(2, 7), "speed": _random.uniform(1.0, 3.0),
                "alpha": _random.uniform(0.15, 0.45),
                "wobble": _random.uniform(0.5, 2.0), "phase": _random.uniform(0, 6.28)
            })

        # Background drawing
        da = Gtk.DrawingArea()
        da.connect("draw", self._draw_bg)
        overlay = Gtk.Overlay()
        overlay.add(da)

        # Main centered container
        outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        outer.set_valign(Gtk.Align.CENTER)
        outer.set_halign(Gtk.Align.CENTER)

        # Card with rounded feel
        card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        card.override_background_color(Gtk.StateFlags.NORMAL, Gdk.RGBA(1, 1, 1, 1.0))
        card.set_size_request(360, -1)

        # Logo
        logo_path = "/home/aquabox/Desktop/Aquabox/Fluxgen-Logo.png"
        if os.path.exists(logo_path):
            pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_scale(logo_path, 420, 120, True)
            logo = Gtk.Image.new_from_pixbuf(pixbuf)
            logo.set_margin_top(8)
            card.pack_start(logo, False, False, 0)

        # Tagline below logo
        tag = Gtk.Label(label="Build a Water-Positive Future")
        tag.override_color(Gtk.StateFlags.NORMAL, Gdk.RGBA(0.3, 0.55, 0.8, 0.6))
        tag.modify_font(Pango.FontDescription("Sans italic 16"))
        tag.set_margin_bottom(2)
        card.pack_start(tag, False, False, 2)

        # Divider
        div = Gtk.DrawingArea()
        div.set_size_request(-1, 2)
        div.set_margin_start(30)
        div.set_margin_end(30)
        div.set_margin_top(4)
        div.set_margin_bottom(4)
        div.connect("draw", self._draw_divider)
        card.pack_start(div, False, False, 0)

        # Sign In label
        signin = Gtk.Label(label="Sign In")
        signin.override_color(Gtk.StateFlags.NORMAL, Gdk.RGBA(0.05, 0.15, 0.4, 1))
        signin.modify_font(Pango.FontDescription("Sans bold 14"))
        signin.set_halign(Gtk.Align.START)
        signin.set_margin_start(30)
        card.pack_start(signin, False, False, 0)

        # Username
        ulabel = Gtk.Label(label="Username")
        ulabel.override_color(Gtk.StateFlags.NORMAL, Gdk.RGBA(0.15, 0.25, 0.45, 1))
        ulabel.modify_font(Pango.FontDescription("Sans bold 18"))
        ulabel.set_halign(Gtk.Align.START)
        ulabel.set_margin_start(30)
        ulabel.set_margin_top(4)
        card.pack_start(ulabel, False, False, 0)

        self.username_entry = Gtk.Entry()
        self.username_entry.set_placeholder_text("Enter your username")
        self.username_entry.modify_font(Pango.FontDescription("Sans 14"))
        self.username_entry.override_background_color(Gtk.StateFlags.NORMAL, Gdk.RGBA(1, 1, 1, 0))
        self.username_entry.set_margin_start(30)
        self.username_entry.set_margin_end(30)
        card.pack_start(self.username_entry, False, False, 4)

        # Password
        plabel = Gtk.Label(label="Password")
        plabel.override_color(Gtk.StateFlags.NORMAL, Gdk.RGBA(0.15, 0.25, 0.45, 1))
        plabel.modify_font(Pango.FontDescription("Sans bold 18"))
        plabel.set_halign(Gtk.Align.START)
        plabel.set_margin_start(30)
        plabel.set_margin_top(3)
        card.pack_start(plabel, False, False, 0)

        self.password_entry = Gtk.Entry()
        self.password_entry.set_placeholder_text("Enter your password")
        self.password_entry.set_visibility(False)
        self.password_entry.modify_font(Pango.FontDescription("Sans 14"))
        self.password_entry.override_background_color(Gtk.StateFlags.NORMAL, Gdk.RGBA(1, 1, 1, 0))
        self.password_entry.set_margin_start(30)
        self.password_entry.set_margin_end(30)
        self.password_entry.connect("activate", self.on_login)
        card.pack_start(self.password_entry, False, False, 4)

        # Error label
        # Check if admin configured credentials
        if not os.path.exists(ADMIN_CONFIG):
            self.error_label = Gtk.Label(label="Admin setup required first")
            self.error_label.override_color(Gtk.StateFlags.NORMAL, Gdk.RGBA(0.8, 0.5, 0.1, 1))
        else:
            self.error_label = Gtk.Label(label="")
        self.error_label.override_color(Gtk.StateFlags.NORMAL, Gdk.RGBA(0.85, 0.15, 0.15, 1))
        self.error_label.modify_font(Pango.FontDescription("Sans bold 14"))
        card.pack_start(self.error_label, False, False, 2)

        # Login button
        btn = Gtk.Button(label="Login  ➜")
        btn.override_background_color(Gtk.StateFlags.NORMAL, Gdk.RGBA(0.06, 0.2, 0.6, 0.5))
        btn.override_color(Gtk.StateFlags.NORMAL, Gdk.RGBA(1, 1, 1, 1))
        btn.modify_font(Pango.FontDescription("Sans bold 18"))
        btn.set_margin_start(30)
        btn.set_margin_end(30)
        btn.set_margin_top(3)
        btn.connect("clicked", self.on_login)
        card.pack_start(btn, False, False, 0)

        admin_btn = Gtk.Button(label="⚙ Admin")
        admin_btn.modify_font(Pango.FontDescription("Sans 12"))
        admin_btn.set_margin_start(30)
        admin_btn.set_margin_end(30)
        admin_btn.set_margin_bottom(6)
        admin_btn.connect("clicked", self._open_admin)
        card.pack_start(admin_btn, False, False, 0)

        outer.pack_start(card, False, False, 0)
        overlay.add_overlay(outer)
        self._login_main = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self._login_main.pack_start(overlay, True, True, 0)
        self.add(self._login_main)

        # Auto-show keyboard when entries focused
        self._login_kb_visible = False
        self._login_kb_shift = False
        self._login_kb_letter_btns = []
        self._active_entry = self.username_entry
        def _on_entry_focus(w, e):
            self._active_entry = w
            self._show_login_kb()
        self.username_entry.connect("focus-in-event", _on_entry_focus)
        self.password_entry.connect("focus-in-event", _on_entry_focus)

        GLib.timeout_add(40, self._animate)

    def _draw_accent(self, widget, cr):
        w = widget.get_allocated_width()
        pat = cairo.LinearGradient(0, 0, w, 0)
        pat.add_color_stop_rgb(0, 0.08, 0.35, 0.8)
        pat.add_color_stop_rgb(0.5, 0.15, 0.55, 0.95)
        pat.add_color_stop_rgb(1, 0.08, 0.35, 0.8)
        cr.set_source(pat)
        cr.rectangle(0, 0, w, 6)
        cr.fill()

    def _draw_divider(self, widget, cr):
        w = widget.get_allocated_width()
        pat = cairo.LinearGradient(0, 0, w, 0)
        pat.add_color_stop_rgba(0, 0.8, 0.85, 0.9, 0)
        pat.add_color_stop_rgba(0.3, 0.7, 0.78, 0.88, 0.6)
        pat.add_color_stop_rgba(0.5, 0.4, 0.6, 0.85, 0.8)
        pat.add_color_stop_rgba(0.7, 0.7, 0.78, 0.88, 0.6)
        pat.add_color_stop_rgba(1, 0.8, 0.85, 0.9, 0)
        cr.set_source(pat)
        cr.rectangle(0, 0, w, 2)
        cr.fill()

    def _animate(self):
        self._wave_offset += 0.04
        self._pulse += 0.02
        now_t = time.time()
        for d in self._drops:
            d["y"] -= d["speed"]
            d["x"] += _math.sin(now_t * d["wobble"] + d["phase"]) * 0.5
            if d["y"] < -15:
                d["y"] = _random.uniform(480, 550)
                d["x"] = _random.uniform(0, 800)
        if now_t - self._last_ripple > 0.8:
            self._ripples.append({"x": _random.uniform(50, 750), "y": _random.uniform(340, 440), "r": 0, "max": _random.uniform(30, 60), "alpha": 0.3})
            self._last_ripple = now_t
        self._ripples = [r for r in self._ripples if r["r"] < r["max"]]
        for r in self._ripples:
            r["r"] += 1.2
        try:
            self._login_main.get_children()[0].get_child().queue_draw()
        except: pass
        self.fullscreen()
        return True

    def _draw_bg(self, widget, cr):
        w = widget.get_allocated_width()
        h = widget.get_allocated_height()

        # White background
        cr.set_source_rgb(1.0, 1.0, 1.0)
        cr.paint()

        t = self._wave_offset

        # Waves at bottom
        for i, (amp, freq, spd, r, g, b_c, alpha) in enumerate([
            (12, 0.018, 1.2, 0.3, 0.65, 0.92, 0.28),
            (8, 0.022, -0.9, 0.4, 0.72, 0.95, 0.2),
            (6, 0.028, 1.5, 0.35, 0.6, 0.88, 0.15),
        ]):
            cr.move_to(0, h)
            base_y = h * 0.76 + i * 14
            for x in range(0, w + 2, 3):
                y = base_y + amp * _math.sin(x * freq + t * spd) + amp * 0.5 * _math.sin(x * freq * 1.7 + t * spd * 0.8 + 1.3)
                cr.line_to(x, y)
            cr.line_to(w, h)
            cr.close_path()
            pat = cairo.LinearGradient(0, base_y - amp, 0, h)
            pat.add_color_stop_rgba(0, r, g, b_c, alpha * 0.5)
            pat.add_color_stop_rgba(1, r * 0.7, g * 0.8, b_c * 0.9, alpha)
            cr.set_source(pat)
            cr.fill()

        # Water drops
        for d in self._drops:
            s = d["r"]
            cr.save()
            cr.translate(d["x"], d["y"])
            pat = cairo.RadialGradient(0, s * 0.3, 0, 0, 0, s)
            pat.add_color_stop_rgba(0, 0.65, 0.88, 1.0, d["alpha"] * 0.9)
            pat.add_color_stop_rgba(0.5, 0.4, 0.72, 0.95, d["alpha"] * 0.5)
            pat.add_color_stop_rgba(1.0, 0.2, 0.55, 0.88, d["alpha"] * 0.1)
            cr.set_source(pat)
            cr.move_to(0, -s * 1.2)
            cr.curve_to(s * 0.6, -s * 0.3, s * 0.8, s * 0.4, 0, s)
            cr.curve_to(-s * 0.8, s * 0.4, -s * 0.6, -s * 0.3, 0, -s * 1.2)
            cr.fill()
            cr.set_source_rgba(1, 1, 1, d["alpha"] * 0.6)
            cr.arc(-s * 0.15, -s * 0.2, s * 0.2, 0, _math.pi * 2)
            cr.fill()
            cr.restore()

        # Ripples
        for r in self._ripples:
            progress = r["r"] / r["max"]
            alpha = r["alpha"] * (1.0 - progress)
            if alpha > 0.01:
                cr.set_source_rgba(0.4, 0.72, 0.95, alpha)
                cr.set_line_width(1.5 * (1.0 - progress * 0.5))
                cr.arc(r["x"], r["y"], r["r"], 0, _math.pi * 2)
                cr.stroke()

    def _toggle_password(self, button):
        self._pass_visible = not self._pass_visible
        self.password_entry.set_visibility(self._pass_visible)
        button.set_label("○" if self._pass_visible else "●")

    def _open_admin(self, button):
        """Open admin login - fullscreen with animation."""
        self._admin_win = Gtk.Window(title="Admin")
        self._admin_win.set_default_size(1024, 600)
        self._admin_win.fullscreen()
        self._admin_win.set_app_paintable(True)

        da = Gtk.DrawingArea()
        da.connect("draw", self._draw_admin_bg)
        overlay = Gtk.Overlay()
        overlay.add(da)
        self._admin_bg_phase = 0
        GLib.timeout_add(50, self._animate_admin_bg, da)

        outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        outer.set_valign(Gtk.Align.CENTER)
        outer.set_halign(Gtk.Align.CENTER)

        card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        card.override_background_color(Gtk.StateFlags.NORMAL, Gdk.RGBA(1, 1, 1, 0.95))
        card.set_size_request(350, -1)

        title = Gtk.Label(label="Admin Settings")
        title.override_color(Gtk.StateFlags.NORMAL, Gdk.RGBA(0.07, 0.15, 0.35, 1))
        title.modify_font(Pango.FontDescription("Sans bold 18"))
        title.set_margin_top(15)
        card.pack_start(title, False, False, 0)

        sub = Gtk.Label(label="Enter admin credentials")
        sub.override_color(Gtk.StateFlags.NORMAL, Gdk.RGBA(0.4, 0.45, 0.55, 1))
        sub.modify_font(Pango.FontDescription("Sans 12"))
        card.pack_start(sub, False, False, 0)

        sep = Gtk.Separator()
        sep.set_margin_start(25)
        sep.set_margin_end(25)
        sep.set_margin_top(6)
        card.pack_start(sep, False, False, 0)

        ul = Gtk.Label(label="Admin Username")
        ul.modify_font(Pango.FontDescription("Sans bold 18"))
        ul.set_halign(Gtk.Align.START)
        ul.set_margin_start(25)
        ul.set_margin_top(6)
        card.pack_start(ul, False, False, 0)
        admin_user = Gtk.Entry()
        admin_user.set_placeholder_text("Enter admin username")
        admin_user.modify_font(Pango.FontDescription("Sans 14"))
        admin_user.set_margin_start(25)
        admin_user.set_margin_end(25)
        card.pack_start(admin_user, False, False, 0)

        pl = Gtk.Label(label="Admin Password")
        pl.modify_font(Pango.FontDescription("Sans bold 18"))
        pl.set_halign(Gtk.Align.START)
        pl.set_margin_start(25)
        pl.set_margin_top(4)
        card.pack_start(pl, False, False, 0)
        admin_pass = Gtk.Entry()
        admin_pass.set_placeholder_text("Enter admin password")
        admin_pass.set_visibility(False)
        admin_pass.modify_font(Pango.FontDescription("Sans 14"))
        admin_pass.set_margin_start(25)
        admin_pass.set_margin_end(25)
        card.pack_start(admin_pass, False, False, 0)

        err = Gtk.Label(label="")
        err.override_color(Gtk.StateFlags.NORMAL, Gdk.RGBA(0.8, 0.1, 0.1, 1))
        err.modify_font(Pango.FontDescription("Sans bold 15"))
        card.pack_start(err, False, False, 0)

        btn_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        btn_box.set_margin_start(25)
        btn_box.set_margin_end(25)
        btn_box.set_margin_bottom(15)

        login_btn = Gtk.Button(label="Login")
        login_btn.override_background_color(Gtk.StateFlags.NORMAL, Gdk.RGBA(0.08, 0.25, 0.69, 1))
        login_btn.override_color(Gtk.StateFlags.NORMAL, Gdk.RGBA(1, 1, 1, 1))
        login_btn.modify_font(Pango.FontDescription("Sans bold 15"))

        back_btn = Gtk.Button(label="Back")
        back_btn.modify_font(Pango.FontDescription("Sans 15"))
        back_btn.connect("clicked", lambda b: self._admin_win.destroy())

        def on_admin_login(btn):
            u = admin_user.get_text().strip()
            p = admin_pass.get_text().strip()
            if u == ADMIN_USER and p == ADMIN_PASS:
                self._admin_win.destroy()
                self._show_admin_settings()
            else:
                err.set_text("Wrong admin credentials")

        login_btn.connect("clicked", on_admin_login)
        admin_pass.connect("activate", on_admin_login)
        btn_box.pack_start(login_btn, True, True, 0)
        btn_box.pack_start(back_btn, True, True, 0)
        card.pack_start(btn_box, False, False, 4)

        outer.pack_start(card, False, False, 0)
        overlay.add_overlay(outer)
        admin_login_main = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        admin_login_main.pack_start(overlay, True, True, 0)
        self._admin_win.add(admin_login_main)

        # GTK keyboard for admin login
        adm_kb_visible = [False]
        adm_kb_box_ref = [None]
        adm_kb_shift = [False]
        adm_kb_letter_btns = []
        adm_active = [admin_user]

        def adm_kb_key(button, key):
            entry = adm_active[0]
            char = key.upper() if adm_kb_shift[0] and key.isalpha() else key
            entry.do_insert_at_cursor(entry, char)
            if adm_kb_shift[0]:
                adm_kb_shift[0] = False
                for b, k in adm_kb_letter_btns:
                    b.set_label(k.lower())

        def adm_kb_shift_toggle(button):
            adm_kb_shift[0] = not adm_kb_shift[0]
            for b, k in adm_kb_letter_btns:
                b.set_label(k.upper() if adm_kb_shift[0] else k.lower())
            if adm_kb_shift[0]:
                button.override_background_color(Gtk.StateFlags.NORMAL, Gdk.RGBA(0.2, 0.5, 0.9, 1))
            else:
                button.override_background_color(Gtk.StateFlags.NORMAL, Gdk.RGBA(0.28, 0.28, 0.32, 1))

        def adm_kb_bksp(button):
            entry = adm_active[0]
            pos = entry.get_position()
            if pos > 0:
                text = entry.get_text()
                entry.set_text(text[:pos-1] + text[pos:])
                entry.set_position(pos - 1)

        def show_adm_kb():
            if adm_kb_visible[0]:
                return
            adm_kb_visible[0] = True
            adm_kb_letter_btns.clear()
            kb = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=1)
            kb.override_background_color(Gtk.StateFlags.NORMAL, Gdk.RGBA(0.15, 0.15, 0.18, 1))
            cr = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
            cr.override_background_color(Gtk.StateFlags.NORMAL, Gdk.RGBA(0.15, 0.15, 0.18, 1))
            cb = Gtk.Button(label="\u2715 Close")
            cb.override_background_color(Gtk.StateFlags.NORMAL, Gdk.RGBA(0.7, 0.15, 0.15, 0.9))
            cb.override_color(Gtk.StateFlags.NORMAL, Gdk.RGBA(1, 1, 1, 1))
            cb.modify_font(Pango.FontDescription("Sans bold 12"))
            cb.connect("clicked", lambda b: hide_adm_kb())
            cr.pack_end(cb, False, False, 4)
            kb.pack_start(cr, False, False, 0)
            for row in [["1","2","3","4","5","6","7","8","9","0"],
                        ["q","w","e","r","t","y","u","i","o","p"],
                        ["a","s","d","f","g","h","j","k","l","@"],
                        ["z","x","c","v","b","n","m","!",".","_"]]:
                rb = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=1, homogeneous=True)
                for key in row:
                    b = Gtk.Button(label=key)
                    b.modify_font(Pango.FontDescription("Sans bold 14"))
                    b.override_background_color(Gtk.StateFlags.NORMAL, Gdk.RGBA(0.28, 0.28, 0.32, 1))
                    b.override_color(Gtk.StateFlags.NORMAL, Gdk.RGBA(1, 1, 1, 1))
                    b.set_size_request(-1, 55)
                    b.connect("clicked", adm_kb_key, key)
                    if key.isalpha():
                        adm_kb_letter_btns.append((b, key))
                    rb.pack_start(b, True, True, 0)
                kb.pack_start(rb, False, False, 0)
            ar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=1)
            sb = Gtk.Button(label="\u21e7")
            sb.modify_font(Pango.FontDescription("Sans bold 14"))
            sb.override_background_color(Gtk.StateFlags.NORMAL, Gdk.RGBA(0.28, 0.28, 0.32, 1))
            sb.override_color(Gtk.StateFlags.NORMAL, Gdk.RGBA(1, 1, 1, 1))
            sb.set_size_request(80, 55)
            sb.connect("clicked", adm_kb_shift_toggle)
            ar.pack_start(sb, False, False, 0)
            sp = Gtk.Button(label="Space")
            sp.modify_font(Pango.FontDescription("Sans bold 14"))
            sp.override_background_color(Gtk.StateFlags.NORMAL, Gdk.RGBA(0.28, 0.28, 0.32, 1))
            sp.override_color(Gtk.StateFlags.NORMAL, Gdk.RGBA(1, 1, 1, 1))
            sp.set_size_request(-1, 55)
            sp.connect("clicked", adm_kb_key, " ")
            ar.pack_start(sp, True, True, 0)
            bk = Gtk.Button(label="\u232b")
            bk.modify_font(Pango.FontDescription("Sans bold 14"))
            bk.override_background_color(Gtk.StateFlags.NORMAL, Gdk.RGBA(0.28, 0.28, 0.32, 1))
            bk.override_color(Gtk.StateFlags.NORMAL, Gdk.RGBA(1, 1, 1, 1))
            bk.set_size_request(80, 55)
            bk.connect("clicked", adm_kb_bksp)
            ar.pack_start(bk, False, False, 0)
            kb.pack_start(ar, False, False, 0)
            admin_login_main.pack_end(kb, False, False, 0)
            kb.show_all()
            adm_kb_box_ref[0] = kb

        def hide_adm_kb():
            if not adm_kb_visible[0]:
                return
            if adm_kb_box_ref[0]:
                adm_kb_box_ref[0].destroy()
                adm_kb_box_ref[0] = None
            adm_kb_visible[0] = False

        def on_adm_focus(w, e):
            adm_active[0] = w
            show_adm_kb()
        admin_user.connect("focus-in-event", on_adm_focus)
        admin_pass.connect("focus-in-event", on_adm_focus)

        self._admin_win.show_all()

    def _animate_admin_bg(self, da):
        self._admin_bg_phase += 0.04
        da.queue_draw()
        if hasattr(self, "_admin_win"):
            try:
                return self._admin_win.get_visible()
            except:
                return False
        return False

    def _draw_admin_bg(self, widget, cr):
        w = widget.get_allocated_width()
        h = widget.get_allocated_height()
        t = self._admin_bg_phase
        pat = cairo.LinearGradient(0, 0, 0, h)
        pat.add_color_stop_rgb(0, 0.05, 0.12, 0.28)
        pat.add_color_stop_rgb(0.5, 0.08, 0.18, 0.38)
        pat.add_color_stop_rgb(1, 0.04, 0.1, 0.22)
        cr.set_source(pat)
        cr.paint()
        for i, (amp, freq, spd, a) in enumerate([
            (10, 0.02, 1.2, 0.15), (7, 0.025, -0.9, 0.1), (5, 0.03, 1.5, 0.08)
        ]):
            cr.move_to(0, h)
            base_y = h * 0.78 + i * 12
            for x in range(0, w + 2, 3):
                y = base_y + amp * _math.sin(x * freq + t * spd)
                cr.line_to(x, y)
            cr.line_to(w, h)
            cr.close_path()
            cr.set_source_rgba(0.2, 0.5, 0.8, a)
            cr.fill()

    def _show_admin_settings(self):
        """Show admin settings page to configure API credentials."""
        dialog = Gtk.Window(title="Admin Settings")
        dialog.set_default_size(1024, 600)
        dialog.fullscreen()
        dialog.override_background_color(Gtk.StateFlags.NORMAL, Gdk.RGBA(0.95, 0.96, 0.98, 1))

        # Re-enforce fullscreen
        def _enforce_fs():
            dialog.fullscreen()
            return True
        GLib.timeout_add_seconds(1, _enforce_fs)

        # Make scrollable
        scroll_admin = Gtk.ScrolledWindow()
        scroll_admin.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        scroll_admin.add(box)
        admin_main = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        admin_main.pack_start(scroll_admin, True, True, 0)
        dialog.add(admin_main)
        box.set_margin_start(20)
        box.set_margin_end(20)
        box.set_margin_top(10)

        title = Gtk.Label(label="AquaGen Configuration")
        title.modify_font(Pango.FontDescription("Sans bold 24"))
        title.override_color(Gtk.StateFlags.NORMAL, Gdk.RGBA(0.07, 0.15, 0.35, 1))
        box.pack_start(title, False, False, 4)

        sub = Gtk.Label(label="Configure your AquaGen login credentials")
        sub.modify_font(Pango.FontDescription("Sans 16"))
        sub.override_color(Gtk.StateFlags.NORMAL, Gdk.RGBA(0.4, 0.45, 0.55, 1))
        box.pack_start(sub, False, False, 4)

        sep = Gtk.Separator()
        box.pack_start(sep, False, False, 6)

        # Username
        ul = Gtk.Label(label="Username")
        ul.modify_font(Pango.FontDescription("Sans bold 20"))
        ul.set_halign(Gtk.Align.START)
        box.pack_start(ul, False, False, 0)
        api_user_entry = Gtk.Entry()
        api_user_entry.set_text(USERNAME)
        api_user_entry.modify_font(Pango.FontDescription("Sans 18"))
        box.pack_start(api_user_entry, False, False, 4)

        # Password
        ppl = Gtk.Label(label="Password")
        ppl.modify_font(Pango.FontDescription("Sans bold 20"))
        ppl.set_halign(Gtk.Align.START)
        box.pack_start(ppl, False, False, 0)
        api_pass_entry = Gtk.Entry()
        api_pass_entry.set_text(PASSWORD)
        api_pass_entry.set_visibility(False)
        api_pass_entry.modify_font(Pango.FontDescription("Sans 18"))
        api_pass_entry.set_icon_from_icon_name(Gtk.EntryIconPosition.SECONDARY, "view-conceal-symbolic")
        def _toggle_pass(entry, icon_pos, event):
            vis = not entry.get_visibility()
            entry.set_visibility(vis)
            entry.set_icon_from_icon_name(Gtk.EntryIconPosition.SECONDARY, "view-reveal-symbolic" if vis else "view-conceal-symbolic")
        api_pass_entry.connect("icon-press", _toggle_pass)
        box.pack_start(api_pass_entry, False, False, 4)

        # Login Type
        ltl = Gtk.Label(label="Login Type")
        ltl.modify_font(Pango.FontDescription("Sans bold 20"))
        ltl.set_halign(Gtk.Align.START)
        box.pack_start(ltl, False, False, 0)
        lt_combo = Gtk.ComboBoxText()
        lt_combo.append_text("DEFAULT")
        lt_combo.append_text("EXTERNAL")
        lt_combo.set_active(0 if LOGIN_TYPE == "DEFAULT" else 1)
        box.pack_start(lt_combo, False, False, 0)

        # Language selection moved to header bar dropdown

        status = Gtk.Label(label="")
        status.modify_font(Pango.FontDescription("Sans bold 18"))
        box.pack_start(status, False, False, 4)

        def on_save(btn):
            new_user = api_user_entry.get_text().strip()
            new_pass = api_pass_entry.get_text().strip()
            new_lt = lt_combo.get_active_text()

            if not new_user or not new_pass:
                status.set_text("Enter both username and password")
                status.override_color(Gtk.StateFlags.NORMAL, Gdk.RGBA(0.8, 0.1, 0.1, 1))
                return

            set_api_credentials(new_user, new_pass, new_lt)

            if save_admin_config(new_user, new_pass, new_lt, TTS_LANG):
                save_session()
                status.set_text("Saved! Credentials updated.")
                status.override_color(Gtk.StateFlags.NORMAL, Gdk.RGBA(0.1, 0.6, 0.2, 1))
            else:
                status.set_text("Save failed!")
                status.override_color(Gtk.StateFlags.NORMAL, Gdk.RGBA(0.8, 0.1, 0.1, 1))

        def on_test(btn):
            old_u, old_p, old_lt = USERNAME, PASSWORD, LOGIN_TYPE
            set_api_credentials(api_user_entry.get_text().strip(), api_pass_entry.get_text().strip(), lt_combo.get_active_text())

            status.set_text("Testing...")
            status.override_color(Gtk.StateFlags.NORMAL, Gdk.RGBA(0.1, 0.3, 0.7, 1))

            def do_test():
                success = get_token()
                def show_result(ok):
                    if ok:
                        status.set_text("Connection successful!")
                        status.override_color(Gtk.StateFlags.NORMAL, Gdk.RGBA(0.1, 0.6, 0.2, 1))
                    else:
                        status.set_text("Connection failed! Check credentials.")
                        status.override_color(Gtk.StateFlags.NORMAL, Gdk.RGBA(0.8, 0.1, 0.1, 1))
                        pass
                GLib.idle_add(show_result, success)
            threading.Thread(target=do_test, daemon=True).start()

        btn_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)

        test_btn = Gtk.Button(label="Test Connection")
        test_btn.override_background_color(Gtk.StateFlags.NORMAL, Gdk.RGBA(0.1, 0.5, 0.8, 1))
        test_btn.override_color(Gtk.StateFlags.NORMAL, Gdk.RGBA(1, 1, 1, 1))
        test_btn.modify_font(Pango.FontDescription("Sans bold 18"))
        test_btn.connect("clicked", on_test)
        btn_box.pack_start(test_btn, True, True, 0)

        save_btn = Gtk.Button(label="Save")
        save_btn.override_background_color(Gtk.StateFlags.NORMAL, Gdk.RGBA(0.1, 0.6, 0.2, 1))
        save_btn.override_color(Gtk.StateFlags.NORMAL, Gdk.RGBA(1, 1, 1, 1))
        save_btn.modify_font(Pango.FontDescription("Sans bold 18"))
        save_btn.connect("clicked", on_save)
        btn_box.pack_start(save_btn, True, True, 0)

        box.pack_start(btn_box, False, False, 5)

        close_btn = Gtk.Button(label="Close")
        close_btn.modify_font(Pango.FontDescription("Sans 18"))
        box.pack_start(close_btn, False, False, 0)

        # GTK keyboard for admin settings
        admin_kb_visible = [False]
        admin_kb_box_ref = [None]
        admin_kb_shift = [False]
        admin_kb_letter_btns = []
        admin_active = [api_user_entry]

        def admin_kb_key(button, key):
            entry = admin_active[0]
            char = key.upper() if admin_kb_shift[0] and key.isalpha() else key
            entry.do_insert_at_cursor(entry, char)
            if admin_kb_shift[0]:
                admin_kb_shift[0] = False
                for btn, k in admin_kb_letter_btns:
                    btn.set_label(k.lower())

        def admin_kb_shift_cb(button):
            admin_kb_shift[0] = not admin_kb_shift[0]
            for btn, k in admin_kb_letter_btns:
                btn.set_label(k.upper() if admin_kb_shift[0] else k.lower())
            if admin_kb_shift[0]:
                button.override_background_color(Gtk.StateFlags.NORMAL, Gdk.RGBA(0.2, 0.5, 0.9, 1))
            else:
                button.override_background_color(Gtk.StateFlags.NORMAL, Gdk.RGBA(0.28, 0.28, 0.32, 1))

        def admin_kb_bksp(button):
            entry = admin_active[0]
            pos = entry.get_position()
            if pos > 0:
                text = entry.get_text()
                entry.set_text(text[:pos-1] + text[pos:])
                entry.set_position(pos - 1)

        def show_admin_kb():
            if admin_kb_visible[0]:
                return
            admin_kb_visible[0] = True
            admin_kb_letter_btns.clear()
            kb = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=1)
            kb.override_background_color(Gtk.StateFlags.NORMAL, Gdk.RGBA(0.15, 0.15, 0.18, 1))
            cr = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
            cr.override_background_color(Gtk.StateFlags.NORMAL, Gdk.RGBA(0.15, 0.15, 0.18, 1))
            cb = Gtk.Button(label="\u2715 Close")
            cb.override_background_color(Gtk.StateFlags.NORMAL, Gdk.RGBA(0.7, 0.15, 0.15, 0.9))
            cb.override_color(Gtk.StateFlags.NORMAL, Gdk.RGBA(1, 1, 1, 1))
            cb.modify_font(Pango.FontDescription("Sans bold 12"))
            cb.connect("clicked", lambda b: hide_admin_kb())
            cr.pack_end(cb, False, False, 4)
            kb.pack_start(cr, False, False, 0)
            for row in [["1","2","3","4","5","6","7","8","9","0"],
                        ["q","w","e","r","t","y","u","i","o","p"],
                        ["a","s","d","f","g","h","j","k","l","@"],
                        ["z","x","c","v","b","n","m","!",".","_"]]:
                rb = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=1, homogeneous=True)
                for key in row:
                    b = Gtk.Button(label=key)
                    b.modify_font(Pango.FontDescription("Sans bold 14"))
                    b.override_background_color(Gtk.StateFlags.NORMAL, Gdk.RGBA(0.28, 0.28, 0.32, 1))
                    b.override_color(Gtk.StateFlags.NORMAL, Gdk.RGBA(1, 1, 1, 1))
                    b.set_size_request(-1, 55)
                    b.connect("clicked", admin_kb_key, key)
                    if key.isalpha():
                        admin_kb_letter_btns.append((b, key))
                    rb.pack_start(b, True, True, 0)
                kb.pack_start(rb, False, False, 0)
            ar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=1)
            sb = Gtk.Button(label="\u21e7")
            sb.modify_font(Pango.FontDescription("Sans bold 14"))
            sb.override_background_color(Gtk.StateFlags.NORMAL, Gdk.RGBA(0.28, 0.28, 0.32, 1))
            sb.override_color(Gtk.StateFlags.NORMAL, Gdk.RGBA(1, 1, 1, 1))
            sb.set_size_request(80, 55)
            sb.connect("clicked", admin_kb_shift_cb)
            ar.pack_start(sb, False, False, 0)
            for sym in ["#","$","-","+"]:
                xb = Gtk.Button(label=sym)
                xb.modify_font(Pango.FontDescription("Sans bold 14"))
                xb.override_background_color(Gtk.StateFlags.NORMAL, Gdk.RGBA(0.28, 0.28, 0.32, 1))
                xb.override_color(Gtk.StateFlags.NORMAL, Gdk.RGBA(1, 1, 1, 1))
                xb.set_size_request(50, 55)
                xb.connect("clicked", admin_kb_key, sym)
                ar.pack_start(xb, False, False, 0)
            sp = Gtk.Button(label="Space")
            sp.modify_font(Pango.FontDescription("Sans bold 14"))
            sp.override_background_color(Gtk.StateFlags.NORMAL, Gdk.RGBA(0.28, 0.28, 0.32, 1))
            sp.override_color(Gtk.StateFlags.NORMAL, Gdk.RGBA(1, 1, 1, 1))
            sp.set_size_request(-1, 55)
            sp.connect("clicked", admin_kb_key, " ")
            ar.pack_start(sp, True, True, 0)
            bk = Gtk.Button(label="\u232b")
            bk.modify_font(Pango.FontDescription("Sans bold 14"))
            bk.override_background_color(Gtk.StateFlags.NORMAL, Gdk.RGBA(0.28, 0.28, 0.32, 1))
            bk.override_color(Gtk.StateFlags.NORMAL, Gdk.RGBA(1, 1, 1, 1))
            bk.set_size_request(80, 55)
            bk.connect("clicked", admin_kb_bksp)
            ar.pack_start(bk, False, False, 0)
            kb.pack_start(ar, False, False, 0)
            admin_main.pack_end(kb, False, False, 0)
            kb.show_all()
            admin_kb_box_ref[0] = kb

        def hide_admin_kb():
            if not admin_kb_visible[0]:
                return
            if admin_kb_box_ref[0]:
                admin_kb_box_ref[0].destroy()
                admin_kb_box_ref[0] = None
            admin_kb_visible[0] = False

        def on_admin_entry_focus(w, e):
            admin_active[0] = w
            show_admin_kb()

        api_user_entry.connect("focus-in-event", on_admin_entry_focus)
        api_pass_entry.connect("focus-in-event", on_admin_entry_focus)

        def close_admin_dialog(b):
            hide_admin_kb()
            dialog.destroy()
        close_btn.connect("clicked", close_admin_dialog)

        dialog.show_all()

    def _show_login_kb(self):
        if self._login_kb_visible:
            return
        self._login_kb_visible = True
        self._login_kb_shift = False
        self._login_kb_letter_btns = []
        self._build_login_gtk_kb()

    def _hide_login_kb(self):
        if not self._login_kb_visible:
            return
        if hasattr(self, '_login_kb_box') and self._login_kb_box:
            self._login_kb_box.destroy()
            self._login_kb_box = None
        self._login_kb_visible = False

    def _build_login_gtk_kb(self):
        """Build GTK keyboard at bottom of login page."""
        self._login_kb_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=1)
        self._login_kb_box.override_background_color(
            Gtk.StateFlags.NORMAL, Gdk.RGBA(0.15, 0.15, 0.18, 1))

        # Close row
        close_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        close_row.override_background_color(
            Gtk.StateFlags.NORMAL, Gdk.RGBA(0.15, 0.15, 0.18, 1))
        kb_close = Gtk.Button(label="\u2715 Close")
        kb_close.override_background_color(
            Gtk.StateFlags.NORMAL, Gdk.RGBA(0.7, 0.15, 0.15, 0.9))
        kb_close.override_color(Gtk.StateFlags.NORMAL, Gdk.RGBA(1, 1, 1, 1))
        kb_close.modify_font(Pango.FontDescription("Sans bold 12"))
        kb_close.connect("clicked", lambda b: self._hide_login_kb())
        close_row.pack_end(kb_close, False, False, 4)
        self._login_kb_box.pack_start(close_row, False, False, 0)

        # Key rows
        rows = [
            ["1", "2", "3", "4", "5", "6", "7", "8", "9", "0"],
            ["q", "w", "e", "r", "t", "y", "u", "i", "o", "p"],
            ["a", "s", "d", "f", "g", "h", "j", "k", "l", "@"],
            ["z", "x", "c", "v", "b", "n", "m", "!", ".", "_"],
        ]
        for row in rows:
            row_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=1, homogeneous=True)
            for key in row:
                btn = Gtk.Button(label=key)
                btn.modify_font(Pango.FontDescription("Sans bold 14"))
                btn.override_background_color(
                    Gtk.StateFlags.NORMAL, Gdk.RGBA(0.28, 0.28, 0.32, 1))
                btn.override_color(Gtk.StateFlags.NORMAL, Gdk.RGBA(1, 1, 1, 1))
                btn.set_size_request(-1, 55)
                btn.connect("clicked", self._login_kb_key, key)
                if key.isalpha():
                    self._login_kb_letter_btns.append((btn, key))
                row_box.pack_start(btn, True, True, 0)
            self._login_kb_box.pack_start(row_box, False, False, 0)

        # Action row
        action_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=1)
        shift_btn = Gtk.Button(label="\u21e7")
        shift_btn.modify_font(Pango.FontDescription("Sans bold 14"))
        shift_btn.override_background_color(Gtk.StateFlags.NORMAL, Gdk.RGBA(0.28, 0.28, 0.32, 1))
        shift_btn.override_color(Gtk.StateFlags.NORMAL, Gdk.RGBA(1, 1, 1, 1))
        shift_btn.set_size_request(80, 55)
        shift_btn.connect("clicked", self._login_kb_shift_cb)
        action_row.pack_start(shift_btn, False, False, 0)

        for sym in ["#", "$", "-", "+"]:
            sbtn = Gtk.Button(label=sym)
            sbtn.modify_font(Pango.FontDescription("Sans bold 14"))
            sbtn.override_background_color(Gtk.StateFlags.NORMAL, Gdk.RGBA(0.28, 0.28, 0.32, 1))
            sbtn.override_color(Gtk.StateFlags.NORMAL, Gdk.RGBA(1, 1, 1, 1))
            sbtn.set_size_request(50, 55)
            sbtn.connect("clicked", self._login_kb_key, sym)
            action_row.pack_start(sbtn, False, False, 0)

        space_btn = Gtk.Button(label="Space")
        space_btn.modify_font(Pango.FontDescription("Sans bold 14"))
        space_btn.override_background_color(Gtk.StateFlags.NORMAL, Gdk.RGBA(0.28, 0.28, 0.32, 1))
        space_btn.override_color(Gtk.StateFlags.NORMAL, Gdk.RGBA(1, 1, 1, 1))
        space_btn.set_size_request(-1, 55)
        space_btn.connect("clicked", self._login_kb_key, " ")
        action_row.pack_start(space_btn, True, True, 0)

        bksp_btn = Gtk.Button(label="\u232b")
        bksp_btn.modify_font(Pango.FontDescription("Sans bold 14"))
        bksp_btn.override_background_color(Gtk.StateFlags.NORMAL, Gdk.RGBA(0.28, 0.28, 0.32, 1))
        bksp_btn.override_color(Gtk.StateFlags.NORMAL, Gdk.RGBA(1, 1, 1, 1))
        bksp_btn.set_size_request(80, 55)
        bksp_btn.connect("clicked", self._login_kb_bksp)
        action_row.pack_start(bksp_btn, False, False, 0)

        enter_btn = Gtk.Button(label="\u23ce")
        enter_btn.modify_font(Pango.FontDescription("Sans bold 14"))
        enter_btn.override_background_color(Gtk.StateFlags.NORMAL, Gdk.RGBA(0.1, 0.5, 0.2, 1))
        enter_btn.override_color(Gtk.StateFlags.NORMAL, Gdk.RGBA(1, 1, 1, 1))
        enter_btn.set_size_request(80, 55)
        enter_btn.connect("clicked", self._login_kb_enter)
        action_row.pack_start(enter_btn, False, False, 0)

        self._login_kb_box.pack_start(action_row, False, False, 0)
        self._login_main.pack_end(self._login_kb_box, False, False, 0)
        self._login_kb_box.show_all()

    def _login_kb_key(self, button, key):
        entry = self._active_entry
        char = key.upper() if self._login_kb_shift and key.isalpha() else key
        entry.do_insert_at_cursor(entry, char)
        if self._login_kb_shift:
            self._login_kb_shift = False
            for btn, k in self._login_kb_letter_btns:
                btn.set_label(k.lower())

    def _login_kb_shift_cb(self, button):
        self._login_kb_shift = not self._login_kb_shift
        for btn, k in self._login_kb_letter_btns:
            btn.set_label(k.upper() if self._login_kb_shift else k.lower())
        if self._login_kb_shift:
            button.override_background_color(Gtk.StateFlags.NORMAL, Gdk.RGBA(0.2, 0.5, 0.9, 1))
        else:
            button.override_background_color(Gtk.StateFlags.NORMAL, Gdk.RGBA(0.28, 0.28, 0.32, 1))

    def _login_kb_bksp(self, button):
        entry = self._active_entry
        pos = entry.get_position()
        if pos > 0:
            text = entry.get_text()
            entry.set_text(text[:pos-1] + text[pos:])
            entry.set_position(pos - 1)

    def _login_kb_enter(self, button):
        if self._active_entry == self.username_entry:
            self.password_entry.grab_focus()
            self._active_entry = self.password_entry
        else:
            self._hide_login_kb()
            self.on_login(None)

    def on_login(self, widget):
        global USERNAME, PASSWORD, LOGGED_IN, LOGIN_TYPE
        u = self.username_entry.get_text().strip()
        p = self.password_entry.get_text().strip()
        if not u or not p:
            self.error_label.set_text("Enter username and password")
            return

        # Check if admin has configured API credentials
        if os.path.exists(ADMIN_CONFIG):
            try:
                with open(ADMIN_CONFIG) as f:
                    cfg = json.load(f)
                saved_user = cfg.get("api_username", "")
                saved_pass = cfg.get("api_password", "")
                if saved_user and saved_pass:
                    # User must enter the same credentials admin set
                    if u != saved_user or p != saved_pass:
                        self.error_label.set_text("Invalid credentials")
                        return
            except:
                pass

        USERNAME = u
        PASSWORD = p
        self.error_label.set_text("Logging in...")
        def try_login():
            success = get_token()
            GLib.idle_add(self._login_result, success)
        threading.Thread(target=try_login, daemon=True).start()

    def _login_result(self, success):
        if success:
            global LOGGED_IN, USERNAME, PASSWORD, LOGIN_TYPE
            LOGGED_IN = True
            save_session()
            self._hide_login_kb()
            # Show transition message
            self.error_label.override_color(Gtk.StateFlags.NORMAL, Gdk.RGBA(0.12, 0.38, 0.75, 1))
            self.error_label.set_text("Welcome! Loading alerts...")
            # Delay window creation slightly for smooth transition
            def _create_alerts_window():
                self.hide()
                win = AlertsWindow()
                win.connect("destroy", lambda w: Gtk.main_quit() if LOGGED_IN else None)
                win.show_all()
                self.destroy()
                return False
            GLib.timeout_add(300, _create_alerts_window)
        else:
            self.error_label.override_color(Gtk.StateFlags.NORMAL, Gdk.RGBA(0.85, 0.15, 0.15, 1))
            self.error_label.set_text("Login failed. Check username/password.")

class AlertsWindow(Gtk.Window):
    def __init__(self):
        super().__init__(title="AquaBox Alerts")
        self.set_default_size(1024, 600)
        self.fullscreen()

        # Apply CSS
        css_provider = Gtk.CssProvider()
        css_provider.load_from_data(CSS.encode())
        Gtk.StyleContext.add_provider_for_screen(
            Gdk.Screen.get_default(), css_provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )

        # Main layout with overlay for announcements
        overlay = Gtk.Overlay()
        self.add(overlay)

        self.main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        overlay.add(self.main_box)

        # Center overlay for typing animation
        # Overlay container with typing label + close button
        self.overlay_container = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.overlay_container.set_halign(Gtk.Align.CENTER)
        self.overlay_container.set_valign(Gtk.Align.CENTER)
        self.overlay_container.get_style_context().add_class("announce-overlay")

        # Close button row
        close_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        close_row.override_background_color(
            Gtk.StateFlags.NORMAL, Gdk.RGBA(0, 0, 0, 0))
        close_btn = Gtk.Button(label="\u2715")
        close_btn.override_color(Gtk.StateFlags.NORMAL, Gdk.RGBA(1, 0.4, 0.4, 1))
        close_btn.override_background_color(Gtk.StateFlags.NORMAL, Gdk.RGBA(0, 0, 0, 0))
        close_btn.modify_font(Pango.FontDescription("Sans bold 18"))
        close_btn.set_relief(Gtk.ReliefStyle.NONE)
        close_btn.connect("clicked", lambda b: self._cancel_announce())
        close_row.pack_end(close_btn, False, False, 4)
        self.overlay_container.pack_start(close_row, False, False, 0)

        # Typing text label
        self.overlay_label = Gtk.Label(label="")
        self.overlay_label.set_line_wrap(True)
        self.overlay_label.set_max_width_chars(80)
        self.overlay_label.override_color(
            Gtk.StateFlags.NORMAL, Gdk.RGBA(1, 1, 1, 1))
        self.overlay_label.modify_font(Pango.FontDescription("Noto Sans bold 18"))
        self.overlay_label.set_margin_start(30)
        self.overlay_label.set_margin_end(30)
        self.overlay_label.set_margin_top(10)
        self.overlay_label.set_margin_bottom(20)
        self.overlay_container.pack_start(self.overlay_label, False, False, 0)

        overlay.add_overlay(self.overlay_container)
        self.overlay_container.set_no_show_all(True)
        self.overlay_container.set_visible(False)

        # Header
        header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        header.get_style_context().add_class("header-bar")

        header_text = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        title = Gtk.Label(label="AquaBox Alerts")
        title.get_style_context().add_class("header-title")
        title.set_halign(Gtk.Align.START)
        self.header_sub = Gtk.Label(label="Fluxgen Sustainable Technologies")
        self.header_sub.get_style_context().add_class("header-sub")
        self.header_sub.set_halign(Gtk.Align.START)
        header_text.pack_start(title, False, False, 0)
        header_text.pack_start(self.header_sub, False, False, 0)
        header.pack_start(header_text, True, True, 0)

        # Right side: Refresh icon button + Clock + Date
        right_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)

        # Refresh icon button (circular)
        self.refresh_btn = Gtk.Button()
        self.refresh_btn.set_size_request(36, 36)
        refresh_icon = Gtk.Label(label="\u21BB")
        refresh_icon.override_color(Gtk.StateFlags.NORMAL, Gdk.RGBA(1, 1, 1, 0.9))
        refresh_icon.modify_font(Pango.FontDescription("Sans 20"))
        self.refresh_btn.add(refresh_icon)
        self.refresh_btn.connect("clicked", self.on_refresh_clicked)
        self.refresh_btn.get_style_context().add_class("refresh-btn")
        right_box.pack_start(self.refresh_btn, False, False, 0)

        # Language dropdown
        self._lang_list = ["en", "te", "kn", "ta", "hi", "ml"]
        self.lang_combo = Gtk.ComboBoxText()
        self.lang_combo.append_text("ENG")
        self.lang_combo.append_text("TEL")
        self.lang_combo.append_text("KAN")
        self.lang_combo.append_text("TAM")
        self.lang_combo.append_text("HIN")
        self.lang_combo.append_text("MAL")
        lang_idx = 0
        for i, l in enumerate(self._lang_list):
            if l == TTS_LANG:
                lang_idx = i
                break
        self.lang_combo.set_active(lang_idx)
        self.lang_combo.get_style_context().add_class("header-lang")
        self.lang_combo.set_size_request(-1, -1)
        self.lang_combo.connect("changed", self._on_lang_changed)
        right_box.pack_start(self.lang_combo, False, False, 0)



        # Separator
        sep = Gtk.Label(label="|")
        sep.override_color(Gtk.StateFlags.NORMAL, Gdk.RGBA(1, 1, 1, 0.25))
        right_box.pack_start(sep, False, False, 0)

        # Clock + Date stacked
        time_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.clock_label = Gtk.Label()
        self.clock_label.get_style_context().add_class("header-clock")
        self.clock_label.set_halign(Gtk.Align.END)
        self.date_label = Gtk.Label()
        self.date_label.get_style_context().add_class("header-date")
        self.date_label.set_halign(Gtk.Align.END)
        time_box.pack_start(self.clock_label, False, False, 0)
        time_box.pack_start(self.date_label, False, False, 0)
        right_box.pack_start(time_box, False, False, 0)

        # Separator before logout
        sep2 = Gtk.Label(label="|")
        sep2.override_color(Gtk.StateFlags.NORMAL, Gdk.RGBA(1, 1, 1, 0.25))
        right_box.pack_start(sep2, False, False, 0)

        # Logout button (arrow out of box symbol)
        logout_btn = Gtk.Button()
        logout_btn.set_size_request(36, 36)
        logout_icon = Gtk.Label(label="→│")
        logout_icon.override_color(Gtk.StateFlags.NORMAL, Gdk.RGBA(1, 0.4, 0.4, 0.9))
        logout_icon.modify_font(Pango.FontDescription("Sans 14"))
        logout_btn.add(logout_icon)
        logout_btn.connect("clicked", self._on_logout)
        logout_btn.get_style_context().add_class("refresh-btn")
        logout_btn.set_tooltip_text("Logout")
        right_box.pack_start(logout_btn, False, False, 0)

        header.pack_end(right_box, False, False, 0)

        self.main_box.pack_start(header, False, False, 0)

        # Stats bar
        self.stats_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8, homogeneous=True)
        self.stats_box.get_style_context().add_class("stats-bar")

        self.stat_unread = self._make_stat("0", "UNREAD", "stat-num-unread")
        self.stat_read = self._make_stat("0", "READ", "stat-num-read")
        self.stat_total = self._make_stat("0", "TOTAL", "stat-num-total")
        self.stat_offline = self._make_stat("0", "OFFLINE", "stat-num-unread")

        self.stat_unread[0].connect("clicked", lambda b: self._scroll_to_section("unread"))
        self.stat_read[0].connect("clicked", lambda b: self._scroll_to_section("read"))
        self.stat_total[0].connect("clicked", lambda b: self._scroll_to_section("top"))
        self.stat_offline[0].connect("clicked", lambda b: self._scroll_to_section("offline"))
        self.stats_box.pack_start(self.stat_unread[0], True, True, 0)
        self.stats_box.pack_start(self.stat_read[0], True, True, 0)
        self.stats_box.pack_start(self.stat_total[0], True, True, 0)
        self.stats_box.pack_start(self.stat_offline[0], True, True, 0)

        self.main_box.pack_start(self.stats_box, False, False, 0)

        # Scrollable alerts area
        scroll = Gtk.ScrolledWindow()
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scroll.get_style_context().add_class("alerts-scroll")
        self.alerts_container = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        scroll.add(self.alerts_container)
        self.main_box.pack_start(scroll, True, True, 0)

        # Bottom section (fixed at bottom)
        bottom_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)

        # Announce typing bar
        self.announce_bar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        self.announce_bar.get_style_context().add_class("announce-bar")
        self.announce_label = Gtk.Label(label="")
        self.announce_label.get_style_context().add_class("announce-text")
        self.announce_label.modify_font(Pango.FontDescription("Noto Sans bold 18"))
        self.announce_label.set_halign(Gtk.Align.START)
        self.announce_bar.pack_start(self.announce_label, True, True, 0)
        self.announce_bar.set_no_show_all(True)
        bottom_box.pack_start(self.announce_bar, False, False, 0)

        # Bottom refresh bar
        refresh_bar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        refresh_bar.get_style_context().add_class("refresh-bar")

        # WiFi button (left)
        self.wifi_btn = Gtk.Button()
        self.wifi_btn.get_style_context().add_class("wifi-btn")
        self.wifi_btn.set_relief(Gtk.ReliefStyle.NONE)
        self._wifi_icon = Gtk.DrawingArea()
        self._wifi_icon.set_size_request(22, 22)
        self._wifi_icon.connect("draw", self._draw_wifi_icon)
        self.wifi_btn.add(self._wifi_icon)
        self.wifi_btn.connect("clicked", self._on_wifi_clicked)
        self.wifi_btn.set_tooltip_text("WiFi Info")
        refresh_bar.pack_start(self.wifi_btn, False, False, 4)

        # Speaker/volume button (next to wifi)
        self.speaker_btn = Gtk.Button()
        self.speaker_btn.get_style_context().add_class("speaker-btn")
        self.speaker_btn.set_relief(Gtk.ReliefStyle.NONE)
        self._speaker_icon = Gtk.DrawingArea()
        self._speaker_icon.set_size_request(22, 22)
        self._speaker_icon.connect("draw", self._draw_speaker_icon)
        self.speaker_btn.add(self._speaker_icon)
        self.speaker_btn.connect("clicked", self._on_speaker_clicked)
        self.speaker_btn.set_tooltip_text("Volume")
        refresh_bar.pack_start(self.speaker_btn, False, False, 4)

        self.refresh_label = Gtk.Label(label="Loading...")
        self.refresh_label.get_style_context().add_class("refresh-text")
        self.refresh_label.set_halign(Gtk.Align.CENTER)
        refresh_bar.pack_start(self.refresh_label, True, True, 0)
        bottom_box.pack_start(refresh_bar, False, False, 0)

        # WiFi popup (hidden by default)
        self._wifi_popup = None
        # Volume popup (hidden by default)
        self._volume_popup = None
        # WiFi connection state monitoring
        self._wifi_connected = True
        GLib.timeout_add(5000, self._check_wifi_status)

        self.main_box.pack_end(bottom_box, False, False, 0)

        # Typing animation state
        self._typing_text = ""
        self._typing_index = 0
        self._typing_timer = None
        self._hide_timer = None
        self._typing_done = True
        self._typing_speed = 55
        self._batch_announcing = False
        self._last_refresh_time = ""
        self._countdown = REFRESH_INTERVAL


        # AquaGPT Panda Mascot
        self._panda_event = Gtk.EventBox()
        self._panda_da = Gtk.DrawingArea()
        self._panda_da.set_size_request(250, 180)

        self._panda_da.connect("draw", self._draw_panda)
        self._panda_event.add(self._panda_da)
        self._panda_event.set_halign(Gtk.Align.END)
        self._panda_event.set_valign(Gtk.Align.END)
        self._panda_event.set_size_request(250, 180)
        self._panda_event.set_margin_end(10)
        self._panda_event.set_margin_bottom(30)
        self._panda_event.connect("button-press-event", self._open_chat)
        # WiFi overlay panel (hidden by default) - added BEFORE panda so it renders below panda initially
        self._wifi_overlay = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        self._wifi_overlay.set_halign(Gtk.Align.START)
        self._wifi_overlay.set_valign(Gtk.Align.END)
        self._wifi_overlay.set_size_request(300, 350)
        self._wifi_overlay.set_margin_bottom(40)
        self._wifi_overlay.set_margin_start(5)
        self._wifi_overlay.override_background_color(
            Gtk.StateFlags.NORMAL, Gdk.RGBA(0.08, 0.18, 0.32, 0.97))
        self._wifi_overlay.set_no_show_all(True)
        self._wifi_overlay.set_visible(False)

        overlay.add_overlay(self._panda_event)
        overlay.add_overlay(self._wifi_overlay)

        self._panda_phase = 0
        self._panda_visible = True
        self._panda_alpha = 1.0
        self._panda_msg_idx = 0
        self._panda_msg_char = 0
        self._panda_messages = [
            "Hi! I am AquaGPT",
            "Your water assistant!",
            "Monitoring your alerts",
            "Stay water positive!",
            "Need help? I am here!",
        ]
        self._panda_current_msg = self._panda_messages[0]

        # Show panda every 60 seconds
        GLib.timeout_add_seconds(10, self._change_panda_msg)
        GLib.timeout_add(50, self._animate_panda)

        # Start fetching
        self.update_clock()
        GLib.timeout_add_seconds(1, self.update_clock)
        GLib.timeout_add_seconds(1, self._update_countdown)
        self._all_today_alerts = []
        self._all_offline_alerts = []
        self._loading_phase = 0
        self._loading_active = True
        self._show_loading()
        GLib.timeout_add(3000, self.first_fetch)  # Wait 3s for network
        GLib.timeout_add_seconds(REFRESH_INTERVAL, self.refresh_alerts)
        # Pre-cache welcome audio for AquaGPT
        def _precache_welcome():
            _tts_generate("Hi! I am AquaGPT, your water assistant. Ask me anything!",
                         "en", "/tmp/aquabox_welcome.mp3", "/tmp/aquabox_welcome.wav")
        threading.Thread(target=_precache_welcome, daemon=True).start()


    def _change_panda_msg(self):
        """Change message every 10 seconds."""
        self._panda_msg_idx += 1
        self._panda_msg_char = 0
        self._panda_current_msg = self._panda_messages[self._panda_msg_idx % len(self._panda_messages)]
        return True

    def _show_panda(self):
        """Show panda mascot popup."""
        if _auto_announcing:
            return True  # Skip during announce
        self._panda_visible = True
        self._panda_alpha = 1.0
        self._panda_msg_char = 0
        self._panda_current_msg = self._panda_messages[self._panda_msg_idx % len(self._panda_messages)]
        self._panda_msg_idx += 1
        self._panda_da.set_visible(True)
        self._panda_da.show()
        return True  # Keep timer

    def _hide_panda(self):
        self._panda_visible = False
        GLib.timeout_add(50, self._fade_panda_out)
        return False

    def _fade_panda_out(self):
        return False

    def _animate_panda(self):
        if self._panda_visible:
            self._panda_phase += 0.08
            self._panda_alpha = 1.0
            if self._panda_msg_char < len(self._panda_current_msg):
                self._panda_msg_char += 1
            self._panda_da.queue_draw()
        return True

    def _draw_panda(self, widget, cr):
        if self._panda_alpha <= 0:
            return
        w = widget.get_allocated_width()
        h = widget.get_allocated_height()
        a = self._panda_alpha

        # Water drop logo with bounce (top area)
        bounce = _math.sin(self._panda_phase * 2) * 3
        logo_path = "/home/aquabox/Desktop/Aquabox/aquagpt-logo.png"
        if os.path.exists(logo_path) and not hasattr(self, "_aquagpt_pixbuf"):
            self._aquagpt_pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_scale(logo_path, 70, 70, True)
        if hasattr(self, "_aquagpt_pixbuf"):
            lw_logo = self._aquagpt_pixbuf.get_width()
            lx = w - lw_logo - 10
            ly = 5 + bounce
            cr.save()
            Gdk.cairo_set_source_pixbuf(cr, self._aquagpt_pixbuf, lx, ly)
            cr.paint_with_alpha(a)
            cr.restore()

        # Message text with typing (middle area, below logo)
        msg = self._panda_current_msg[:self._panda_msg_char]
        if msg:
            cr.save()
            cr.select_font_face("Noto Sans", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
            cr.set_font_size(13)
            ext = cr.text_extents(msg)
            tx = w - ext.width - 10
            ty = 100

            # Text shadow
            cr.set_source_rgba(0, 0, 0, a * 0.15)
            cr.move_to(tx + 1, ty + 1)
            cr.show_text(msg)

            # Text
            cr.set_source_rgba(0.08, 0.3, 0.65, a * 0.8)
            cr.move_to(tx, ty)
            cr.show_text(msg)
            cr.restore()

        # AquaGPT label (bottom)
        cr.save()
        cr.select_font_face("Noto Sans", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
        cr.set_source_rgba(0.1, 0.4, 0.8, a * 0.5)
        cr.set_font_size(11)
        cr.move_to(w - 75, h - 10)
        cr.show_text("AquaGPT")
        cr.restore()


    def _open_chat(self, widget, event):
        """Open AquaGPT chat interface."""
        if hasattr(self, '_chat_window') and self._chat_window and self._chat_window.get_visible():
            self._chat_window.present()
            return

        self._chat_window = Gtk.Window(title="AquaGPT")
        self._chat_window.set_default_size(1024, 600)
        self._chat_window.fullscreen()

        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)

        # Header
        header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        header.override_background_color(Gtk.StateFlags.NORMAL, Gdk.RGBA(0.08, 0.25, 0.55, 1))
        header.set_size_request(-1, 60)

        # Logo in header
        logo_path = "/home/aquabox/Desktop/Aquabox/fluxgen-icon.jpg"
        if os.path.exists(logo_path):
            pb = GdkPixbuf.Pixbuf.new_from_file_at_scale(logo_path, 40, 40, True)
            logo_img = Gtk.Image.new_from_pixbuf(pb)
            logo_img.set_margin_start(10)
            header.pack_start(logo_img, False, False, 0)

        title = Gtk.Label(label="AquaGPT")
        title.override_color(Gtk.StateFlags.NORMAL, Gdk.RGBA(1, 1, 1, 1))
        title.modify_font(Pango.FontDescription("Sans bold 22"))
        header.pack_start(title, False, False, 0)

        subtitle = Gtk.Label(label="Your Water Assistant")
        subtitle.override_color(Gtk.StateFlags.NORMAL, Gdk.RGBA(0.7, 0.85, 1, 0.8))
        subtitle.modify_font(Pango.FontDescription("Sans 16"))
        header.pack_start(subtitle, False, False, 0)

        close_btn = Gtk.Button(label="✕")
        close_btn.override_color(Gtk.StateFlags.NORMAL, Gdk.RGBA(1, 0.5, 0.5, 1))
        close_btn.override_background_color(Gtk.StateFlags.NORMAL, Gdk.RGBA(0, 0, 0, 0))
        close_btn.modify_font(Pango.FontDescription("Sans bold 18"))
        close_btn.set_relief(Gtk.ReliefStyle.NONE)
        def _close_chat(b):
            self._hide_chat_kb()
            subprocess.run(["killall", "aplay"], capture_output=True)
            self._chat_window.hide()
        close_btn.connect("clicked", _close_chat)
        header.pack_end(close_btn, False, False, 5)

        main_box.pack_start(header, False, False, 0)

        # Chat messages area
        scroll = Gtk.ScrolledWindow()
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scroll.override_background_color(Gtk.StateFlags.NORMAL, Gdk.RGBA(0.96, 0.97, 0.98, 1))

        self._chat_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        self._chat_box.set_margin_start(10)
        self._chat_box.set_margin_end(10)
        self._chat_box.set_margin_top(10)
        scroll.add(self._chat_box)
        main_box.pack_start(scroll, True, True, 0)

        # Welcome message - start typing immediately, speak in background
        welcome_text = "Hi! I am AquaGPT, your water assistant. Ask me anything!"
        self._add_bot_message(welcome_text, speak=True)

        # Input area
        input_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        input_box.override_background_color(Gtk.StateFlags.NORMAL, Gdk.RGBA(1, 1, 1, 1))
        input_box.set_margin_start(8)
        input_box.set_margin_end(8)
        input_box.set_margin_top(6)
        input_box.set_margin_bottom(8)

        self._chat_entry = Gtk.Entry()
        self._chat_entry.set_placeholder_text("Type your question...")
        self._chat_entry.modify_font(Pango.FontDescription("Sans 18"))
        self._chat_entry.connect("activate", self._send_chat)
        self._chat_entry.connect("focus-in-event", lambda w, e: self._show_chat_kb())
        input_box.pack_start(self._chat_entry, True, True, 0)

        # Mic button with image
        mic_btn = Gtk.Button()
        mic_pb = GdkPixbuf.Pixbuf.new_from_file_at_scale("/home/aquabox/Desktop/Aquabox/mic.jpg", 28, 28, True)
        mic_img = Gtk.Image.new_from_pixbuf(mic_pb)
        mic_btn.add(mic_img)
        mic_btn.set_tooltip_text("Voice input")
        mic_btn.connect("clicked", self._voice_input)
        input_box.pack_start(mic_btn, False, False, 0)

        send_btn = Gtk.Button(label="Send")
        send_btn.override_background_color(Gtk.StateFlags.NORMAL, Gdk.RGBA(0.08, 0.4, 0.75, 1))
        send_btn.override_color(Gtk.StateFlags.NORMAL, Gdk.RGBA(1, 1, 1, 1))
        send_btn.modify_font(Pango.FontDescription("Sans bold 18"))
        send_btn.connect("clicked", self._send_chat)
        input_box.pack_start(send_btn, False, False, 0)

        main_box.pack_start(input_box, False, False, 0)

        self._chat_kb_visible = False
        self._chat_window.add(main_box)
        self._chat_window.show_all()

    def _add_bot_message(self, text, speak=False):
        msg_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        msg_box.set_margin_top(4)
        msg_box.set_margin_start(5)

        # Bot avatar - Fluxgen icon
        icon_path = "/home/aquabox/Desktop/Aquabox/fluxgen-icon.jpg"
        if os.path.exists(icon_path):
            pb = GdkPixbuf.Pixbuf.new_from_file_at_scale(icon_path, 24, 24, True)
            avatar = Gtk.Image.new_from_pixbuf(pb)
        else:
            avatar = Gtk.Label(label="B")
        msg_box.pack_start(avatar, False, False, 0)

        # Bubble
        bubble = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        bubble.override_background_color(Gtk.StateFlags.NORMAL, Gdk.RGBA(0.93, 0.95, 0.98, 1))
        bubble.set_margin_end(40)

        label = Gtk.Label(label="")
        label.set_line_wrap(True)
        label.set_max_width_chars(60)
        label.set_halign(Gtk.Align.START)
        label.modify_font(Pango.FontDescription("Noto Sans 18"))
        label.override_color(Gtk.StateFlags.NORMAL, Gdk.RGBA(0.1, 0.15, 0.3, 1))
        label.set_margin_start(10)
        label.set_margin_end(10)
        label.set_margin_top(8)
        label.set_margin_bottom(8)
        bubble.pack_start(label, False, False, 0)
        msg_box.pack_start(bubble, True, True, 0)

        self._chat_box.pack_start(msg_box, False, False, 0)
        msg_box.show_all()
        try:
            adj = self._chat_box.get_parent().get_vadjustment()
            adj.set_value(adj.get_upper())
        except: pass

        # Typing animation
        self._chat_typing_text = text
        self._chat_typing_idx = 0
        self._chat_typing_label = label
        GLib.timeout_add(25, self._chat_type_tick)

        # Speak answer
        if speak and text:
            def do_speak():
                try:
                    # Use pre-cached welcome audio if available
                    wav = "/tmp/aquabox_welcome.wav" if os.path.exists("/tmp/aquabox_welcome.wav") and "AquaGPT" in text else None
                    if not wav:
                        if _tts_generate(text, "en", "/tmp/aquabox_chat.mp3", "/tmp/aquabox_chat.wav"):
                            wav = "/tmp/aquabox_chat.wav"
                    if wav:
                        subprocess.run(["aplay", "-D", "default", "-q", wav], capture_output=True, timeout=30)
                except Exception as e:
                    print("[AquaBox Chat] Speak error: " + str(e))
            threading.Thread(target=do_speak, daemon=True).start()

    def _chat_type_tick(self):
        if self._chat_typing_idx <= len(self._chat_typing_text):
            self._chat_typing_label.set_text(self._chat_typing_text[:self._chat_typing_idx])
            self._chat_typing_idx += 1
            try:
                adj = self._chat_box.get_parent().get_vadjustment()
                adj.set_value(adj.get_upper())
            except: pass
            return True
        return False


    def _add_user_message(self, text):
        msg_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        msg_box.set_margin_top(4)
        msg_box.set_margin_end(5)

        # User bubble
        bubble = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        bubble.override_background_color(Gtk.StateFlags.NORMAL, Gdk.RGBA(0.08, 0.35, 0.7, 1))
        bubble.set_margin_start(80)

        label = Gtk.Label(label=text)
        label.set_line_wrap(True)
        label.set_max_width_chars(60)
        label.set_halign(Gtk.Align.END)
        label.modify_font(Pango.FontDescription("Noto Sans 18"))
        label.override_color(Gtk.StateFlags.NORMAL, Gdk.RGBA(1, 1, 1, 1))
        label.set_margin_start(10)
        label.set_margin_end(10)
        label.set_margin_top(8)
        label.set_margin_bottom(8)
        bubble.pack_start(label, False, False, 0)

        msg_box.pack_end(bubble, True, True, 0)
        self._chat_box.pack_start(msg_box, False, False, 0)
        msg_box.show_all()
        GLib.idle_add(self._scroll_chat_bottom)

    def _scroll_chat_bottom(self):
        try:
            adj = self._chat_box.get_parent().get_vadjustment()
            adj.set_value(adj.get_upper())
        except: pass
        return False

    def _send_chat(self, widget):
        text = self._chat_entry.get_text().strip()
        if not text:
            return
        self._add_user_message(text)
        self._chat_entry.set_text("")

        # Show thinking animation
        thinking_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        thinking_box.set_margin_top(6)
        thinking_box.set_margin_start(8)
        thinking_box.set_margin_bottom(6)
        icon_path = "/home/aquabox/Desktop/Aquabox/fluxgen-icon.jpg"
        if os.path.exists(icon_path):
            tpb = GdkPixbuf.Pixbuf.new_from_file_at_scale(icon_path, 32, 32, True)
            tavatar = Gtk.Image.new_from_pixbuf(tpb)
        else:
            tavatar = Gtk.Label(label="B")
        thinking_box.pack_start(tavatar, False, False, 0)

        # Animated canvas for thinking
        thinking_bubble = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        thinking_bubble.override_background_color(
            Gtk.StateFlags.NORMAL, Gdk.RGBA(0.91, 0.93, 0.97, 1))
        thinking_da = Gtk.DrawingArea()
        thinking_da.set_size_request(220, 50)
        self._thinking_active = True
        self._thinking_phase = 0.0

        def draw_thinking(widget, cr):
            w = widget.get_allocated_width()
            h = widget.get_allocated_height()
            t = self._thinking_phase
            cy = h / 2

            for i in range(3):
                delay = i * 0.55
                wave = _math.sin(t * 1.6 - delay)
                bounce = -max(0, wave) * 10
                progress = max(0, wave)

                x = 28 + i * 26
                y = cy + bounce

                # Pulse ring (expanding when dot is up)
                if progress > 0.3:
                    ring_r = 8 + progress * 6
                    ring_a = (progress - 0.3) * 0.15
                    cr.set_source_rgba(0.2, 0.5, 0.9, ring_a)
                    cr.set_line_width(1.2)
                    cr.arc(x, y, ring_r, 0, 2 * _math.pi)
                    cr.stroke()

                # Shadow
                shadow_scale = 1.0 - progress * 0.3
                cr.set_source_rgba(0.1, 0.2, 0.4, 0.08 * shadow_scale)
                cr.save()
                cr.scale(1.0, 0.4)
                cr.arc(x, (cy + 8) / 0.4, 7, 0, 2 * _math.pi)
                cr.fill()
                cr.restore()

                # Dot with gradient feel
                size = 6.5 + 2 * progress
                r = 0.15 + 0.15 * progress
                g = 0.4 + 0.2 * progress
                b = 0.75 + 0.15 * progress
                alpha = 0.5 + 0.5 * progress
                cr.set_source_rgba(r, g, b, alpha)
                cr.arc(x, y, size, 0, 2 * _math.pi)
                cr.fill()

                # Glass highlight
                cr.set_source_rgba(0.7, 0.88, 1.0, alpha * 0.5)
                cr.arc(x - size * 0.2, y - size * 0.25, size * 0.4, 0, 2 * _math.pi)
                cr.fill()

            # "AquaGPT is thinking" text with fade
            cr.select_font_face("Sans", cairo.FONT_SLANT_ITALIC, cairo.FONT_WEIGHT_NORMAL)
            cr.set_font_size(12)
            txt_alpha = 0.35 + 0.2 * _math.sin(t * 1.0)
            cr.set_source_rgba(0.25, 0.35, 0.55, txt_alpha)
            cr.move_to(105, cy + 5)
            cr.show_text("AquaGPT is thinking...")

        thinking_da.connect("draw", draw_thinking)
        thinking_bubble.pack_start(thinking_da, False, False, 6)
        thinking_box.pack_start(thinking_bubble, False, False, 0)
        self._chat_box.pack_start(thinking_box, False, False, 0)
        thinking_box.show_all()

        def animate_thinking():
            if not self._thinking_active:
                return False
            self._thinking_phase += 0.04
            thinking_da.queue_draw()
            return True
        GLib.timeout_add(35, animate_thinking)

        # Get answer in background
        def get_answer():
            answer = self._get_ai_answer(text)
            wav_path = None
            try:
                if _tts_generate(answer, "en", "/tmp/aquabox_chat.mp3", "/tmp/aquabox_chat.wav"):
                    wav_path = "/tmp/aquabox_chat.wav"
            except: pass
            self._thinking_active = False
            def show_answer():
                thinking_box.destroy()
                self._add_bot_message(answer)
            GLib.idle_add(show_answer)
            if wav_path:
                time.sleep(0.3)
                subprocess.run(["aplay", "-D", "default", "-q", wav_path], capture_output=True, timeout=30)
        threading.Thread(target=get_answer, daemon=True).start()

    def _draw_mic_icon(self, widget, cr):
        w = widget.get_allocated_width()
        h = widget.get_allocated_height()
        cx, cy = w / 2, h / 2
        # Mic body
        cr.set_source_rgba(1, 1, 1, 1)
        cr.move_to(cx - 4, cy - 8)
        cr.line_to(cx - 4, cy + 2)
        cr.arc(cx, cy + 2, 4, _math.pi, 0)
        cr.line_to(cx + 4, cy - 8)
        cr.arc(cx, cy - 8, 4, 0, _math.pi)
        cr.fill()
        # Stand arc
        cr.set_line_width(1.5)
        cr.arc(cx, cy + 2, 7, _math.pi * 0.15, _math.pi * 0.85)
        cr.stroke()
        # Stand line
        cr.move_to(cx, cy + 9)
        cr.line_to(cx, cy + 12)
        cr.stroke()
        # Base
        cr.move_to(cx - 4, cy + 12)
        cr.line_to(cx + 4, cy + 12)
        cr.stroke()

    def _voice_input(self, button):
        """Record voice and convert to text."""
        button.set_label("...")
        self._add_bot_message("Listening... (Voice input coming soon)")
        button.set_label("Mic")

    def _toggle_chat_kb(self):
        if self._chat_kb_visible:
            self._hide_chat_kb()
        else:
            self._show_chat_kb()

    def _show_chat_kb(self):
        if self._chat_kb_visible:
            return
        self._chat_kb_visible = True
        self._chat_kb_shift = False
        self._chat_kb_letter_btns = []
        self._build_chat_gtk_kb()
        pass  # keyboard shown

    def _hide_chat_kb(self):
        if not self._chat_kb_visible:
            return
        if hasattr(self, '_chat_kb_box') and self._chat_kb_box:
            self._chat_kb_box.destroy()
            self._chat_kb_box = None
        pass  # keyboard hidden
        self._chat_kb_visible = False

    def _build_chat_gtk_kb(self):
        """Build GTK keyboard embedded at bottom of chat."""
        self._chat_kb_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=1)
        self._chat_kb_box.override_background_color(
            Gtk.StateFlags.NORMAL, Gdk.RGBA(0.15, 0.15, 0.18, 1))

        # Close row
        close_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        close_row.override_background_color(
            Gtk.StateFlags.NORMAL, Gdk.RGBA(0.15, 0.15, 0.18, 1))
        kb_close = Gtk.Button(label="\u2715 Close")
        kb_close.override_background_color(
            Gtk.StateFlags.NORMAL, Gdk.RGBA(0.7, 0.15, 0.15, 0.9))
        kb_close.override_color(Gtk.StateFlags.NORMAL, Gdk.RGBA(1, 1, 1, 1))
        kb_close.modify_font(Pango.FontDescription("Sans bold 12"))
        kb_close.connect("clicked", lambda b: self._hide_chat_kb())
        close_row.pack_end(kb_close, False, False, 4)
        self._chat_kb_box.pack_start(close_row, False, False, 0)

        # Key rows
        rows = [
            ["1", "2", "3", "4", "5", "6", "7", "8", "9", "0"],
            ["q", "w", "e", "r", "t", "y", "u", "i", "o", "p"],
            ["a", "s", "d", "f", "g", "h", "j", "k", "l", "?"],
            ["z", "x", "c", "v", "b", "n", "m", "!", ".", "@"],
        ]
        for row in rows:
            row_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=1, homogeneous=True)
            for key in row:
                btn = Gtk.Button(label=key)
                btn.modify_font(Pango.FontDescription("Sans bold 14"))
                btn.override_background_color(
                    Gtk.StateFlags.NORMAL, Gdk.RGBA(0.28, 0.28, 0.32, 1))
                btn.override_color(Gtk.StateFlags.NORMAL, Gdk.RGBA(1, 1, 1, 1))
                btn.set_size_request(-1, 55)
                btn.connect("clicked", self._chat_gtk_key, key)
                if key.isalpha():
                    self._chat_kb_letter_btns.append((btn, key))
                row_box.pack_start(btn, True, True, 0)
            self._chat_kb_box.pack_start(row_box, False, False, 0)

        # Action row
        action_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=1)

        shift_btn = Gtk.Button(label="\u21e7")
        shift_btn.modify_font(Pango.FontDescription("Sans bold 14"))
        shift_btn.override_background_color(
            Gtk.StateFlags.NORMAL, Gdk.RGBA(0.28, 0.28, 0.32, 1))
        shift_btn.override_color(Gtk.StateFlags.NORMAL, Gdk.RGBA(1, 1, 1, 1))
        shift_btn.set_size_request(80, 55)
        shift_btn.connect("clicked", self._chat_gtk_shift)
        action_row.pack_start(shift_btn, False, False, 0)

        space_btn = Gtk.Button(label="Space")
        space_btn.modify_font(Pango.FontDescription("Sans bold 14"))
        space_btn.override_background_color(
            Gtk.StateFlags.NORMAL, Gdk.RGBA(0.28, 0.28, 0.32, 1))
        space_btn.override_color(Gtk.StateFlags.NORMAL, Gdk.RGBA(1, 1, 1, 1))
        space_btn.set_size_request(-1, 55)
        space_btn.connect("clicked", self._chat_gtk_key, " ")
        action_row.pack_start(space_btn, True, True, 0)

        bksp_btn = Gtk.Button(label="\u232b")
        bksp_btn.modify_font(Pango.FontDescription("Sans bold 14"))
        bksp_btn.override_background_color(
            Gtk.StateFlags.NORMAL, Gdk.RGBA(0.28, 0.28, 0.32, 1))
        bksp_btn.override_color(Gtk.StateFlags.NORMAL, Gdk.RGBA(1, 1, 1, 1))
        bksp_btn.set_size_request(80, 55)
        bksp_btn.connect("clicked", self._chat_gtk_bksp)
        action_row.pack_start(bksp_btn, False, False, 0)

        send_btn = Gtk.Button(label="Send")
        send_btn.modify_font(Pango.FontDescription("Sans bold 14"))
        send_btn.override_background_color(
            Gtk.StateFlags.NORMAL, Gdk.RGBA(0.1, 0.5, 0.2, 1))
        send_btn.override_color(Gtk.StateFlags.NORMAL, Gdk.RGBA(1, 1, 1, 1))
        send_btn.set_size_request(80, 55)
        send_btn.connect("clicked", lambda b: (self._send_chat(b), self._hide_chat_kb()))
        action_row.pack_start(send_btn, False, False, 0)

        self._chat_kb_box.pack_start(action_row, False, False, 0)

        # Get the chat window's main container and pack keyboard at bottom
        chat_container = self._chat_window.get_child()
        chat_container.pack_end(self._chat_kb_box, False, False, 0)
        self._chat_kb_box.show_all()

    def _chat_gtk_key(self, button, key):
        char = key.upper() if self._chat_kb_shift and key.isalpha() else key
        self._chat_entry.do_insert_at_cursor(self._chat_entry, char)
        if self._chat_kb_shift:
            self._chat_kb_shift = False
            for btn, k in self._chat_kb_letter_btns:
                btn.set_label(k.lower())

    def _chat_gtk_shift(self, button):
        self._chat_kb_shift = not self._chat_kb_shift
        for btn, k in self._chat_kb_letter_btns:
            btn.set_label(k.upper() if self._chat_kb_shift else k.lower())
        if self._chat_kb_shift:
            button.override_background_color(
                Gtk.StateFlags.NORMAL, Gdk.RGBA(0.2, 0.5, 0.9, 1))
        else:
            button.override_background_color(
                Gtk.StateFlags.NORMAL, Gdk.RGBA(0.28, 0.28, 0.32, 1))

    def _chat_gtk_bksp(self, button):
        pos = self._chat_entry.get_position()
        if pos > 0:
            text = self._chat_entry.get_text()
            self._chat_entry.set_text(text[:pos-1] + text[pos:])
            self._chat_entry.set_position(pos - 1)

    def _get_ai_answer(self, question):
        """Get answer using DuckDuckGo Instant Answer API."""
        try:
            q = question.lower()

            # Water-related built-in answers
            water_qa = {
                "what is water": "Water (H2O) is a transparent, tasteless, odorless substance that is essential for all known forms of life.",
                "save water": "Tips to save water: Fix leaks, use low-flow fixtures, collect rainwater, reuse greywater, and water plants in early morning.",
                "water quality": "Water quality is measured by pH, turbidity, dissolved oxygen, TDS, and presence of contaminants like bacteria or heavy metals.",
                "what is tds": "TDS (Total Dissolved Solids) measures the total amount of dissolved substances in water. Safe drinking water should have TDS below 500 mg/L.",
                "what is ph": "pH measures how acidic or basic water is on a scale of 0-14. Pure water has a pH of 7. Drinking water should be between 6.5-8.5.",
                "water positive": "Water positive means replenishing more water than you consume. Fluxgen helps organizations achieve water positivity through smart monitoring.",
                "what is aquabox": "AquaBox is a water monitoring and alert system by Fluxgen Sustainable Technologies. It monitors water levels, flow rates, and sends real-time alerts.",
                "what is fluxgen": "Fluxgen Sustainable Technologies builds IoT solutions for water management, helping organizations become water-positive.",
                "who are you": "I am AquaBox, your AI water assistant by Fluxgen Sustainable Technologies. I help monitor water usage and answer water-related questions.",
                "hello": "Hello! I am AquaBox. How can I help you with water management today?",
                "hi": "Hi there! I am AquaBox, your water assistant. Ask me anything about water!",
            }

            for key, answer in water_qa.items():
                if key in q:
                    return answer

            # Try DuckDuckGo API
            resp = requests.get(
                "https://api.duckduckgo.com/",
                params={"q": question, "format": "json", "no_html": "1"},
                timeout=10
            )
            data = resp.json()

            # Check for instant answer
            if data.get("AbstractText"):
                return data["AbstractText"][:300]
            if data.get("Answer"):
                return data["Answer"]
            if data.get("Definition"):
                return data["Definition"]
            if data.get("RelatedTopics") and len(data["RelatedTopics"]) > 0:
                topic = data["RelatedTopics"][0]
                if isinstance(topic, dict) and topic.get("Text"):
                    return topic["Text"][:300]

            return "I am still learning! For now, I can answer water-related questions. Try asking about water quality, TDS, pH, or water saving tips."

        except Exception as e:
            return "Sorry, I could not find an answer right now. Please try again later."

    def _scroll_to_section(self, section):
        """Scroll alerts list to a specific section."""
        target = None
        if section == "unread" and hasattr(self, '_section_unread'):
            target = self._section_unread
        elif section == "read" and hasattr(self, '_section_read'):
            target = self._section_read
        elif section == "offline" and hasattr(self, '_section_offline'):
            target = self._section_offline
        elif section == "top":
            # Scroll to top
            adj = self.alerts_container.get_parent().get_vadjustment()
            adj.set_value(0)
            return

        if target:
            def do_scroll():
                alloc = target.get_allocation()
                adj = self.alerts_container.get_parent().get_vadjustment()
                adj.set_value(alloc.y)
            GLib.idle_add(do_scroll)

    def _update_counters(self, delta):
        """Instantly update unread/read counters."""
        try:
            cur_unread = int(self.stat_unread[1].get_text())
            cur_read = int(self.stat_read[1].get_text())
            self.stat_unread[1].set_text(str(max(0, cur_unread - delta)))
            self.stat_read[1].set_text(str(cur_read + delta))
        except Exception:
            pass

    def _make_stat(self, num, label, css_class):
        btn = Gtk.Button()
        btn.set_relief(Gtk.ReliefStyle.NONE)
        btn.get_style_context().add_class("stat-box")
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        num_label = Gtk.Label(label=num)
        num_label.get_style_context().add_class("stat-num")
        num_label.get_style_context().add_class(css_class)
        text_label = Gtk.Label(label=label)
        text_label.get_style_context().add_class("stat-label")
        box.pack_start(num_label, False, False, 0)
        box.pack_start(text_label, False, False, 0)
        btn.add(box)
        return (btn, num_label)

    def update_clock(self):
        self.clock_label.set_text(datetime.now().strftime("%I:%M:%S %p"))
        self.date_label.set_text(datetime.now().strftime("%d %b %Y, %A"))
        # Re-enforce fullscreen if something knocked us out
        self.fullscreen()
        return True

    def _update_countdown(self):
        """Decrease countdown every second and update refresh bar."""
        if self._countdown > 0:
            self._countdown -= 1
        ts = self._last_refresh_time or "--:--:--"
        self.refresh_label.set_text(
            f"Refreshed: {ts} | "
            f"Next: {self._countdown}s | "
            f"{datetime.now().strftime('%d %b %Y')}"
        )
        return True

    # ==================== Loading Animation ====================

    def _show_loading(self):
        """Show AquaGPT logo with breathing animation while loading."""
        for child in self.alerts_container.get_children():
            self.alerts_container.remove(child)

        loading_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        loading_box.set_valign(Gtk.Align.CENTER)
        loading_box.set_halign(Gtk.Align.CENTER)

        logo_path = "/home/aquabox/Desktop/Aquabox/aquagpt-logo.png"
        if os.path.exists(logo_path):
            self._loading_logo = GdkPixbuf.Pixbuf.new_from_file_at_scale(logo_path, 60, 60, True)
        else:
            self._loading_logo = None

        self._loading_da = Gtk.DrawingArea()
        self._loading_da.set_size_request(200, 120)
        self._loading_da.connect("draw", self._draw_loading)
        loading_box.pack_start(self._loading_da, False, False, 10)

        self._loading_label = Gtk.Label(label="Fetching alerts")
        self._loading_label.modify_font(Pango.FontDescription("Sans bold 18"))
        self._loading_label.override_color(Gtk.StateFlags.NORMAL, Gdk.RGBA(0.12, 0.3, 0.6, 1))
        loading_box.pack_start(self._loading_label, False, False, 0)

        sub = Gtk.Label(label="Connecting to AquaGen...")
        sub.modify_font(Pango.FontDescription("Sans 15"))
        sub.override_color(Gtk.StateFlags.NORMAL, Gdk.RGBA(0.4, 0.5, 0.65, 0.7))
        loading_box.pack_start(sub, False, False, 0)

        self.alerts_container.pack_start(loading_box, True, True, 0)
        self.alerts_container.show_all()
        GLib.timeout_add(40, self._tick_loading)
        GLib.timeout_add(500, self._tick_loading_text)

    def _draw_loading(self, widget, cr):
        """Draw AquaGPT logo with slow breathing and water reflection."""
        w = widget.get_allocated_width()
        h = widget.get_allocated_height()
        cx, cy = w / 2, h / 2 - 10
        t = self._loading_phase

        breathe = _math.sin(t * 0.8) * 4

        # Shadow
        cr.set_source_rgba(0.1, 0.2, 0.4, 0.08)
        cr.save()
        cr.scale(1.0, 0.3)
        cr.arc(cx, (cy + 45) / 0.3, 28, 0, 2 * _math.pi)
        cr.fill()
        cr.restore()

        # Logo with breathing
        if self._loading_logo:
            cr.save()
            lw = self._loading_logo.get_width()
            lh = self._loading_logo.get_height()
            scale = 1.0 + 0.03 * _math.sin(t * 0.8)
            cr.translate(cx, cy + breathe)
            cr.scale(scale, scale)
            cr.translate(-lw / 2, -lh / 2)
            Gdk.cairo_set_source_pixbuf(cr, self._loading_logo, 0, 0)
            cr.paint()
            cr.restore()

            # Reflection
            cr.save()
            ref_y = cy + breathe + lh / 2 + 6
            cr.translate(cx, ref_y)
            cr.scale(scale, -scale * 0.35)
            cr.translate(-lw / 2, -lh / 2)
            Gdk.cairo_set_source_pixbuf(cr, self._loading_logo, 0, 0)
            cr.paint_with_alpha(0.1 + 0.03 * _math.sin(t * 0.6))
            cr.restore()

        # Water line
        wave_y = cy + 48
        cr.set_line_width(1)
        cr.move_to(cx - 50, wave_y)
        for x in range(int(cx - 50), int(cx + 51)):
            y = wave_y + 1.5 * _math.sin((x - cx) * 0.08 + t * 0.6)
            cr.line_to(x, y)
        cr.set_source_rgba(0.3, 0.55, 0.85, 0.2)
        cr.stroke()

    def _tick_loading(self):
        if not self._loading_active:
            return False
        self._loading_phase += 0.03
        if hasattr(self, '_loading_da'):
            self._loading_da.queue_draw()
        return True

    def _tick_loading_text(self):
        if not self._loading_active:
            return False
        dots = ["", ".", "..", "..."]
        idx = int(self._loading_phase * 2) % len(dots)
        if hasattr(self, '_loading_label'):
            self._loading_label.set_text(f"Fetching alerts{dots[idx]}")
        return True

    # ==================== WiFi & Volume Controls ====================

    _tailscale_restart_count = 0

    def _check_wifi_status(self):
        """Periodically check WiFi, auto-reconnect, restart Tailscale, and refresh on recovery."""
        # Use nmcli to check actual WiFi state (iwgetid not available on this system)
        try:
            out = subprocess.run(
                ["nmcli", "-t", "-f", "GENERAL.STATE,GENERAL.CONNECTION", "device", "show", "wlan0"],
                capture_output=True, text=True, timeout=3
            )
            state_line = out.stdout.strip()
            connected = "GENERAL.STATE:100" in state_line  # 100 = fully connected
            is_connecting = any(x in state_line for x in ["GENERAL.STATE:40", "GENERAL.STATE:50", "GENERAL.STATE:60", "GENERAL.STATE:70", "GENERAL.STATE:80", "GENERAL.STATE:90"])
            # Save SSID when connected
            if connected:
                try:
                    ssid_out = subprocess.run(
                        ["nmcli", "-t", "-f", "GENERAL.CONNECTION", "device", "show", "wlan0"],
                        capture_output=True, text=True, timeout=3
                    )
                    ssid = ssid_out.stdout.strip().split(":")[-1].replace("netplan-wlan0-", "")
                    if ssid:
                        self._last_ssid = ssid
                except: pass
        except Exception:
            connected = False
            is_connecting = False

        # Check internet only when WiFi is connected
        internet = False
        if connected:
            try:
                requests.get("https://prod-aquagen.azurewebsites.net", timeout=5)
                internet = True
            except Exception:
                pass

        was_disconnected = not self._wifi_connected

        if not connected and not is_connecting:
            # Truly disconnected — wait 3 cycles (15s) before attempting reconnect
            if not hasattr(self, '_reconnect_count'):
                self._reconnect_count = 0
            self._reconnect_count += 1
            if self._reconnect_count >= 3:
                self._reconnect_count = 0
                try:
                    subprocess.run(
                        ["sudo", "nmcli", "connection", "up", "netplan-wlan0-" + self._last_ssid] if hasattr(self, '_last_ssid') and self._last_ssid else
                        ["sudo", "nmcli", "device", "connect", "wlan0"],
                        capture_output=True, timeout=10
                    )
                    print(f"[{now()}] WiFi reconnect attempted")
                except Exception:
                    pass
            GLib.idle_add(self.refresh_label.set_text, "WiFi disconnected - reconnecting...")
            print(f"[{now()}] WiFi disconnected - waiting before reconnect ({getattr(self,'_reconnect_count',0)}/3)...")
        elif is_connecting:
            print(f"[{now()}] WiFi connecting - waiting for DHCP...")
        else:
            self._reconnect_count = 0

        if connected != self._wifi_connected:
            self._wifi_connected = connected
            GLib.idle_add(self._wifi_icon.queue_draw)

        if connected and internet and was_disconnected:
            # Just reconnected - restart Tailscale and refresh alerts
            print(f"[{now()}] WiFi + Internet restored! Restarting Tailscale...")
            subprocess.run(["sudo", "systemctl", "restart", "tailscaled"],
                           capture_output=True, timeout=15)
            self._tailscale_restart_count = 0
            print(f"[{now()}] Refreshing token and alerts...")
            GLib.idle_add(self.refresh_label.set_text, "Network restored - Refreshing...")
            self._countdown = REFRESH_INTERVAL
            self._last_fetch_time_actual = 0
            global token, token_time
            token = ""
            token_time = 0
            threading.Thread(target=self._fetch_and_update, daemon=True).start()

        # Periodically restart Tailscale if WiFi connected but no internet (every 5 min)
        if connected and not internet:
            self._tailscale_restart_count += 1
            if self._tailscale_restart_count >= 60:  # 60 * 5s = 5 minutes
                print(f"[{now()}] WiFi up but no internet - restarting Tailscale...")
                subprocess.run(["sudo", "systemctl", "restart", "tailscaled"],
                               capture_output=True, timeout=15)
                self._tailscale_restart_count = 0

        return True

    def _draw_wifi_icon(self, widget, cr):
        """Draw a WiFi icon - white when connected, red when disconnected."""
        w = widget.get_allocated_width()
        h = widget.get_allocated_height()
        cx, cy = w / 2, h * 0.75
        if self._wifi_connected:
            cr.set_source_rgb(1, 1, 1)  # White
        else:
            cr.set_source_rgb(0.95, 0.2, 0.2)  # Red
        cr.set_line_width(2)
        cr.set_line_cap(cairo.LINE_CAP_ROUND)
        for r in [4, 8, 12]:
            cr.arc(cx, cy, r, _math.pi * 1.25, _math.pi * 1.75)
            cr.stroke()
        cr.arc(cx, cy, 1.5, 0, 2 * _math.pi)
        cr.fill()
        # Draw X over icon when disconnected
        if not self._wifi_connected:
            cr.set_source_rgb(0.95, 0.2, 0.2)
            cr.set_line_width(2)
            cr.move_to(w * 0.2, h * 0.2)
            cr.line_to(w * 0.8, h * 0.8)
            cr.stroke()
            cr.move_to(w * 0.8, h * 0.2)
            cr.line_to(w * 0.2, h * 0.8)
            cr.stroke()

    def _draw_speaker_icon(self, widget, cr):
        """Draw a speaker icon."""
        w = widget.get_allocated_width()
        h = widget.get_allocated_height()
        cr.set_source_rgb(1, 1, 1)
        # Speaker body
        cr.rectangle(w * 0.15, h * 0.35, w * 0.2, h * 0.3)
        cr.fill()
        # Speaker cone
        cr.move_to(w * 0.35, h * 0.35)
        cr.line_to(w * 0.55, h * 0.15)
        cr.line_to(w * 0.55, h * 0.85)
        cr.line_to(w * 0.35, h * 0.65)
        cr.close_path()
        cr.fill()
        # Sound waves
        cr.set_line_width(1.5)
        cr.set_line_cap(cairo.LINE_CAP_ROUND)
        for r in [5, 9]:
            cr.arc(w * 0.55, h * 0.5, r, -_math.pi * 0.35, _math.pi * 0.35)
            cr.stroke()

    def _get_wifi_info(self):
        """Get current WiFi SSID and signal strength using nmcli."""
        ssid = ""
        signal = ""
        try:
            # Get active SSID from nmcli
            out = subprocess.run(
                ["nmcli", "-t", "-f", "active,ssid,signal", "dev", "wifi"],
                capture_output=True, text=True, timeout=3
            )
            for line in out.stdout.strip().split("\n"):
                parts = line.split(":")
                if len(parts) >= 3 and parts[0].strip().lower() == "yes":
                    ssid = parts[1].strip()
                    sig_val = parts[2].strip()
                    if sig_val.isdigit():
                        pct = int(sig_val)
                        if pct >= 80:
                            signal = f"{pct}% (Excellent)"
                        elif pct >= 60:
                            signal = f"{pct}% (Good)"
                        elif pct >= 40:
                            signal = f"{pct}% (Fair)"
                        else:
                            signal = f"{pct}% (Weak)"
                    break
        except Exception:
            pass
        return ssid or "Not connected", signal or "N/A"

    def _scan_wifi_networks(self):
        """Scan for available WiFi networks using nmcli."""
        networks = []
        try:
            # Rescan first
            subprocess.run(["sudo", "nmcli", "device", "wifi", "rescan"],
                           capture_output=True, timeout=10)
            import time as _t; _t.sleep(2)
            out = subprocess.run(
                ["nmcli", "-t", "-f", "SSID,SIGNAL,SECURITY,IN-USE", "device", "wifi", "list"],
                capture_output=True, text=True, timeout=10
            )
            seen = {}
            for line in out.stdout.strip().split("\n"):
                if not line.strip():
                    continue
                parts = line.split(":")
                if len(parts) >= 3:
                    ssid = parts[0].strip()
                    if not ssid:
                        continue
                    try:
                        sig = int(parts[1].strip())
                    except ValueError:
                        sig = 0
                    security = parts[2].strip() if len(parts) > 2 else ""
                    in_use = parts[3].strip() if len(parts) > 3 else ""
                    locked = security != "" and security != "--"
                    if ssid not in seen or sig > seen[ssid]["signal"]:
                        seen[ssid] = {"ssid": ssid, "signal": sig, "locked": locked, "in_use": in_use == "*"}
            networks = sorted(seen.values(), key=lambda x: x["signal"], reverse=True)
        except Exception as e:
            print(f"[{now()}] WiFi scan error: {e}")
        return networks

    def _connect_to_wifi(self, ssid, password, status_label, on_done=None):
        """Connect to a WiFi network in background thread."""
        def _status(text, r=0.59, g=0.75, b=0.98):
            GLib.idle_add(lambda: status_label.set_text(text))
            GLib.idle_add(lambda: status_label.override_color(
                Gtk.StateFlags.NORMAL, Gdk.RGBA(r, g, b, 1)))

        def do_connect():
            _status(f"Connecting to {ssid}...")
            import time as _time
            connected = False
            try:
                # Try nmcli first (NetworkManager)
                nmcli_check = subprocess.run(["which", "nmcli"], capture_output=True, timeout=3)
                if nmcli_check.returncode == 0:
                    # Delete existing connection if any
                    subprocess.run(
                        ["sudo", "nmcli", "connection", "delete", ssid],
                        capture_output=True, timeout=5
                    )
                    if password:
                        result = subprocess.run(
                            ["sudo", "nmcli", "device", "wifi", "connect", ssid,
                             "password", password, "ifname", "wlan0"],
                            capture_output=True, text=True, timeout=30
                        )
                    else:
                        result = subprocess.run(
                            ["sudo", "nmcli", "device", "wifi", "connect", ssid,
                             "ifname", "wlan0"],
                            capture_output=True, text=True, timeout=30
                        )
                    if result.returncode == 0:
                        connected = True
                    else:
                        print(f"[{now()}] nmcli failed: {result.stderr.strip()}, trying wpa_cli...")
            except Exception:
                pass

            if not connected:
                try:
                    # Fallback: wpa_cli
                    out = subprocess.run(
                        ["sudo", "wpa_cli", "-i", "wlan0", "add_network"],
                        capture_output=True, text=True, timeout=5
                    )
                    net_id = out.stdout.strip().split("\n")[-1]

                    subprocess.run(
                        ["sudo", "wpa_cli", "-i", "wlan0", "set_network", net_id,
                         "ssid", f'"{ssid}"'],
                        capture_output=True, text=True, timeout=5
                    )
                    if password:
                        subprocess.run(
                            ["sudo", "wpa_cli", "-i", "wlan0", "set_network", net_id,
                             "psk", f'"{password}"'],
                            capture_output=True, text=True, timeout=5
                        )
                    else:
                        subprocess.run(
                            ["sudo", "wpa_cli", "-i", "wlan0", "set_network", net_id,
                             "key_mgmt", "NONE"],
                            capture_output=True, text=True, timeout=5
                        )

                    subprocess.run(
                        ["sudo", "wpa_cli", "-i", "wlan0", "enable_network", net_id],
                        capture_output=True, timeout=5
                    )
                    subprocess.run(
                        ["sudo", "wpa_cli", "-i", "wlan0", "select_network", net_id],
                        capture_output=True, timeout=5
                    )
                    subprocess.run(
                        ["sudo", "wpa_cli", "-i", "wlan0", "save_config"],
                        capture_output=True, timeout=5
                    )
                except Exception as e:
                    _status(f"Error: {e}", 0.95, 0.2, 0.2)
                    return

            # Wait for connection using nmcli (iwgetid not available)
            for i in range(20):
                _time.sleep(1)
                _status(f"Connecting to {ssid}... ({i+1}s)")
                try:
                    chk = subprocess.run(
                        ["nmcli", "-t", "-f", "GENERAL.STATE,GENERAL.CONNECTION", "device", "show", "wlan0"],
                        capture_output=True, text=True, timeout=3
                    )
                    wifi_ok = "GENERAL.STATE:100" in chk.stdout
                except Exception:
                    wifi_ok = False
                if wifi_ok:
                    # Get IP via DHCP
                    subprocess.run(["sudo", "dhclient", "wlan0"], capture_output=True, timeout=10)
                    _status(f"Connected to {ssid}!", 0.26, 0.85, 0.37)
                    self._wifi_connected = True
                    self._last_ssid = ssid
                    GLib.idle_add(self._wifi_icon.queue_draw)
                    if on_done:
                        GLib.idle_add(on_done)
                    # Close GTK keyboard if open
                    if hasattr(self, '_hide_wifi_kb_func') and self._hide_wifi_kb_func:
                        GLib.idle_add(self._hide_wifi_kb_func)
                    # Save to wpa_supplicant.conf for persistence
                    self._save_wifi_config(ssid, password)
                    # Restart Tailscale so remote access works on new network
                    print(f"[{now()}] Restarting Tailscale for new network...")
                    subprocess.run(["sudo", "systemctl", "restart", "tailscaled"],
                                   capture_output=True, timeout=15)
                    # Refresh token and alerts
                    print(f"[{now()}] WiFi changed to {ssid}, refreshing alerts...")
                    global token, token_time
                    token = ""
                    token_time = 0
                    self._last_fetch_time_actual = 0
                    self._countdown = REFRESH_INTERVAL
                    threading.Thread(target=self._fetch_and_update, daemon=True).start()
                    return

            _status("Failed to connect. Check password.", 0.95, 0.2, 0.2)
            if on_done:
                GLib.idle_add(on_done)

        threading.Thread(target=do_connect, daemon=True).start()

    def _save_wifi_config(self, ssid, password):
        """Save WiFi credentials to wpa_supplicant.conf for boot persistence."""
        try:
            if password:
                # Generate PSK hash
                result = subprocess.run(
                    ["wpa_passphrase", ssid, password],
                    capture_output=True, text=True, timeout=5
                )
                block = result.stdout.strip()
            else:
                block = f'network={{\n\tssid="{ssid}"\n\tkey_mgmt=NONE\n}}'

            # Append to wpa_supplicant.conf if not already there
            check = subprocess.run(
                ["sudo", "grep", "-c", f'ssid="{ssid}"', "/etc/wpa_supplicant/wpa_supplicant.conf"],
                capture_output=True, text=True, timeout=3
            )
            if check.stdout.strip() == "0" or check.returncode != 0:
                subprocess.run(
                    ["sudo", "bash", "-c", f'echo \'\n{block}\' >> /etc/wpa_supplicant/wpa_supplicant.conf'],
                    capture_output=True, timeout=5
                )
                print(f"[{now()}] Saved WiFi config for {ssid}")
        except Exception as e:
            print(f"[{now()}] Failed to save WiFi config: {e}")

    def _disconnect_wifi(self, status_label):
        """Disconnect from current WiFi using nmcli."""
        try:
            current_ssid, _ = self._get_wifi_info()
            subprocess.run(
                ["sudo", "nmcli", "device", "disconnect", "wlan0"],
                capture_output=True, timeout=5
            )
            self._wifi_connected = False
            GLib.idle_add(self._wifi_icon.queue_draw)
            status_label.set_text("Disconnected.")
            status_label.override_color(Gtk.StateFlags.NORMAL, Gdk.RGBA(0.98, 0.75, 0.15, 1))
        except Exception as e:
            status_label.set_text(f"Error: {e}")

    def _on_wifi_clicked(self, button):
        """Toggle WiFi manager overlay panel."""
        if self._wifi_overlay.get_visible():
            self._wifi_overlay.set_visible(False)
            # Restore panda
            if hasattr(self, '_panda_event'):
                self._panda_event.set_visible(True)
            return
        # Hide panda and announce overlay so they don't cover wifi panel
        if hasattr(self, '_panda_event'):
            self._panda_event.set_visible(False)
        if hasattr(self, 'overlay_container'):
            self.overlay_container.set_visible(False)
        self._build_wifi_panel()
        # Must temporarily allow show_all to propagate
        self._wifi_overlay.set_no_show_all(False)
        self._wifi_overlay.show_all()
        self._wifi_overlay.set_no_show_all(True)
        self._wifi_overlay.set_visible(True)
        # Hide password box initially
        if hasattr(self, '_wifi_pass_box'):
            self._wifi_pass_box.hide()

    def _build_wifi_panel(self):
        """Build WiFi panel with two pages: network list and connect form."""
        for child in self._wifi_overlay.get_children():
            child.destroy()

        # Use a Gtk.Stack for page switching
        stack = Gtk.Stack()
        stack.set_transition_type(Gtk.StackTransitionType.SLIDE_LEFT_RIGHT)
        stack.set_transition_duration(200)
        self._wifi_stack = stack

        # ========== PAGE 1: Network List ==========
        page1 = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
        page1.set_margin_start(10)
        page1.set_margin_end(10)
        page1.set_margin_top(8)
        page1.set_margin_bottom(8)

        current_ssid, current_signal = self._get_wifi_info()

        # Header
        header_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        title = Gtk.Label(label="WiFi Settings")
        title.get_style_context().add_class("wifi-ssid")
        title.set_halign(Gtk.Align.START)
        header_row.pack_start(title, True, True, 0)
        close_btn = Gtk.Button(label="\u2715")
        close_btn.override_color(Gtk.StateFlags.NORMAL, Gdk.RGBA(1, 0.4, 0.4, 1))
        close_btn.override_background_color(Gtk.StateFlags.NORMAL, Gdk.RGBA(0, 0, 0, 0))
        close_btn.set_relief(Gtk.ReliefStyle.NONE)
        close_btn.connect("clicked", lambda b: self._close_wifi_popup())
        header_row.pack_end(close_btn, False, False, 0)
        page1.pack_start(header_row, False, False, 0)

        # Current connection
        if self._wifi_connected and current_ssid != "Not connected":
            conn_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
            conn_label = Gtk.Label(label=f"\u2705 {current_ssid}  ({current_signal})")
            conn_label.get_style_context().add_class("wifi-net-connected")
            conn_label.set_halign(Gtk.Align.START)
            conn_box.pack_start(conn_label, True, True, 0)
            disc_btn = Gtk.Button(label="Disconnect")
            disc_btn.get_style_context().add_class("wifi-disconnect-btn")
            page1.pack_start(conn_box, False, False, 0)
        else:
            no_conn = Gtk.Label(label="\u274C  Not connected")
            no_conn.override_color(Gtk.StateFlags.NORMAL, Gdk.RGBA(0.95, 0.2, 0.2, 1))
            no_conn.set_halign(Gtk.Align.START)
            page1.pack_start(no_conn, False, False, 0)

        sep = Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL)
        page1.pack_start(sep, False, False, 2)

        # Scan row
        scan_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        scan_label = Gtk.Label(label="Available Networks")
        scan_label.get_style_context().add_class("wifi-ssid")
        scan_label.set_halign(Gtk.Align.START)
        scan_row.pack_start(scan_label, True, True, 0)
        scan_btn = Gtk.Button(label="\u21BB Scan")
        scan_btn.get_style_context().add_class("wifi-scan-btn")
        scan_row.pack_end(scan_btn, False, False, 0)
        page1.pack_start(scan_row, False, False, 0)

        # Network list
        scroll = Gtk.ScrolledWindow()
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scroll.set_size_request(-1, 180)
        net_list = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        scroll.add(net_list)
        page1.pack_start(scroll, True, True, 0)

        # Status on page 1
        p1_status = Gtk.Label(label="")
        p1_status.get_style_context().add_class("wifi-status-label")
        p1_status.set_halign(Gtk.Align.START)
        page1.pack_start(p1_status, False, False, 2)

        # Wire disconnect
        if self._wifi_connected and current_ssid != "Not connected":
            disc_btn.connect("clicked", lambda b: self._disconnect_wifi(p1_status))
            conn_box.pack_end(disc_btn, False, False, 0)

        stack.add_named(page1, "list")

        # ========== PAGE 2: Connect Form ==========
        page2 = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        page2.set_margin_start(10)
        page2.set_margin_end(10)
        page2.set_margin_top(8)
        page2.set_margin_bottom(8)

        # Header with back button
        p2_header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        back_btn = Gtk.Button(label="\u2190  Back")
        back_btn.get_style_context().add_class("wifi-scan-btn")
        def go_back(b):
            subprocess.run(["killall", "wvkbd-mobintl"], capture_output=True)
            self._wifi_kb_visible = False
            stack.set_visible_child_name("list")
        back_btn.connect("clicked", go_back)
        p2_header.pack_start(back_btn, False, False, 0)

        p2_title = Gtk.Label(label="Connect to WiFi")
        p2_title.get_style_context().add_class("wifi-ssid")
        p2_header.pack_start(p2_title, True, True, 0)

        p2_close = Gtk.Button(label="\u2715")
        p2_close.override_color(Gtk.StateFlags.NORMAL, Gdk.RGBA(1, 0.4, 0.4, 1))
        p2_close.override_background_color(Gtk.StateFlags.NORMAL, Gdk.RGBA(0, 0, 0, 0))
        p2_close.set_relief(Gtk.ReliefStyle.NONE)
        p2_close.connect("clicked", lambda b: self._close_wifi_popup())
        p2_header.pack_end(p2_close, False, False, 0)
        page2.pack_start(p2_header, False, False, 0)

        sep2 = Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL)
        page2.pack_start(sep2, False, False, 2)

        # WiFi Name (read-only)
        ssid_lbl = Gtk.Label(label="WiFi Name")
        ssid_lbl.get_style_context().add_class("wifi-signal")
        ssid_lbl.set_halign(Gtk.Align.START)
        page2.pack_start(ssid_lbl, False, False, 0)

        self._wifi_ssid_entry = Gtk.Entry()
        self._wifi_ssid_entry.set_editable(False)
        self._wifi_ssid_entry.get_style_context().add_class("wifi-pass-entry")
        page2.pack_start(self._wifi_ssid_entry, False, False, 0)

        # Password
        pass_lbl = Gtk.Label(label="Password")
        pass_lbl.get_style_context().add_class("wifi-signal")
        pass_lbl.set_halign(Gtk.Align.START)
        page2.pack_start(pass_lbl, False, False, 0)

        pass_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        self._wifi_pass_entry = Gtk.Entry()
        self._wifi_pass_entry.set_placeholder_text("Enter password")
        self._wifi_pass_entry.set_visibility(False)
        self._wifi_pass_entry.get_style_context().add_class("wifi-pass-entry")
        pass_row.pack_start(self._wifi_pass_entry, True, True, 0)

        show_pass_btn = Gtk.Button(label="\u25C9")
        show_pass_btn.set_relief(Gtk.ReliefStyle.NONE)
        show_pass_btn.override_background_color(Gtk.StateFlags.NORMAL, Gdk.RGBA(0, 0, 0, 0))
        def toggle_pass_vis(b):
            vis = not self._wifi_pass_entry.get_visibility()
            self._wifi_pass_entry.set_visibility(vis)
        show_pass_btn.connect("clicked", toggle_pass_vis)
        pass_row.pack_start(show_pass_btn, False, False, 0)
        page2.pack_start(pass_row, False, False, 0)

        # Status label for page 2
        p2_status = Gtk.Label(label="")
        p2_status.get_style_context().add_class("wifi-status-label")
        p2_status.set_halign(Gtk.Align.START)
        p2_status.set_line_wrap(True)

        # GTK Keyboard for WiFi password
        self._wifi_kb_visible = False
        self._wifi_kb_box = None
        self._wifi_kb_shift = [False]
        self._wifi_kb_letter_btns = []

        def wifi_kb_key(button, key):
            entry = self._wifi_pass_entry
            char = key.upper() if self._wifi_kb_shift[0] and key.isalpha() else key
            entry.do_insert_at_cursor(entry, char)
            if self._wifi_kb_shift[0]:
                self._wifi_kb_shift[0] = False
                for b, k in self._wifi_kb_letter_btns:
                    b.set_label(k.lower())

        def wifi_kb_shift_cb(button):
            self._wifi_kb_shift[0] = not self._wifi_kb_shift[0]
            for b, k in self._wifi_kb_letter_btns:
                b.set_label(k.upper() if self._wifi_kb_shift[0] else k.lower())
            if self._wifi_kb_shift[0]:
                button.override_background_color(Gtk.StateFlags.NORMAL, Gdk.RGBA(0.2, 0.5, 0.9, 1))
            else:
                button.override_background_color(Gtk.StateFlags.NORMAL, Gdk.RGBA(0.28, 0.28, 0.32, 1))

        def wifi_kb_bksp(button):
            entry = self._wifi_pass_entry
            pos = entry.get_position()
            if pos > 0:
                text = entry.get_text()
                entry.set_text(text[:pos-1] + text[pos:])
                entry.set_position(pos - 1)

        self._wifi_kb_closing = False
        def show_wifi_kb():
            if self._wifi_kb_visible or self._wifi_kb_closing:
                return
            self._wifi_kb_visible = True
            self._wifi_kb_letter_btns.clear()
            # Move wifi panel to top
            self._wifi_overlay.set_valign(Gtk.Align.START)
            self._wifi_overlay.set_margin_top(5)
            self._wifi_overlay.set_margin_bottom(0)
            self._wifi_overlay.set_size_request(300, 200)

            kb = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=1)
            kb.override_background_color(Gtk.StateFlags.NORMAL, Gdk.RGBA(0.15, 0.15, 0.18, 1))

            # Close button row
            cr = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
            cr.override_background_color(Gtk.StateFlags.NORMAL, Gdk.RGBA(0.15, 0.15, 0.18, 1))
            cb = Gtk.Button(label="\u2715 Close")
            cb.override_background_color(Gtk.StateFlags.NORMAL, Gdk.RGBA(0.7, 0.15, 0.15, 0.9))
            cb.override_color(Gtk.StateFlags.NORMAL, Gdk.RGBA(1, 1, 1, 1))
            cb.modify_font(Pango.FontDescription("Sans bold 12"))
            cb.set_can_focus(False)
            def _do_close_wifi_kb(b):
                self._wifi_kb_closing = True
                hide_wifi_kb()
                GLib.timeout_add(800, lambda: setattr(self, '_wifi_kb_closing', False) or False)
            cb.connect("clicked", _do_close_wifi_kb)
            cr.pack_end(cb, False, False, 4)
            kb.pack_start(cr, False, False, 0)

            for row in [["1","2","3","4","5","6","7","8","9","0"],
                        ["q","w","e","r","t","y","u","i","o","p"],
                        ["a","s","d","f","g","h","j","k","l","@"],
                        ["z","x","c","v","b","n","m","!",".","_"]]:
                rb = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=1, homogeneous=True)
                for key in row:
                    b = Gtk.Button(label=key)
                    b.modify_font(Pango.FontDescription("Sans bold 14"))
                    b.override_background_color(Gtk.StateFlags.NORMAL, Gdk.RGBA(0.28, 0.28, 0.32, 1))
                    b.override_color(Gtk.StateFlags.NORMAL, Gdk.RGBA(1, 1, 1, 1))
                    b.set_size_request(-1, 55)
                    b.set_can_focus(False)
                    b.connect("clicked", wifi_kb_key, key)
                    if key.isalpha():
                        self._wifi_kb_letter_btns.append((b, key))
                    rb.pack_start(b, True, True, 0)
                kb.pack_start(rb, False, False, 0)
            ar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=1)
            sb = Gtk.Button(label="\u21e7")
            sb.modify_font(Pango.FontDescription("Sans bold 14"))
            sb.override_background_color(Gtk.StateFlags.NORMAL, Gdk.RGBA(0.28, 0.28, 0.32, 1))
            sb.override_color(Gtk.StateFlags.NORMAL, Gdk.RGBA(1, 1, 1, 1))
            sb.set_size_request(80, 55)
            sb.set_can_focus(False)
            sb.connect("clicked", wifi_kb_shift_cb)
            ar.pack_start(sb, False, False, 0)
            for sym in ["#","$","-","+"]:
                xb = Gtk.Button(label=sym)
                xb.modify_font(Pango.FontDescription("Sans bold 14"))
                xb.override_background_color(Gtk.StateFlags.NORMAL, Gdk.RGBA(0.28, 0.28, 0.32, 1))
                xb.override_color(Gtk.StateFlags.NORMAL, Gdk.RGBA(1, 1, 1, 1))
                xb.set_size_request(50, 55)
                xb.set_can_focus(False)
                xb.connect("clicked", wifi_kb_key, sym)
                ar.pack_start(xb, False, False, 0)
            sp = Gtk.Button(label="Space")
            sp.modify_font(Pango.FontDescription("Sans bold 14"))
            sp.override_background_color(Gtk.StateFlags.NORMAL, Gdk.RGBA(0.28, 0.28, 0.32, 1))
            sp.override_color(Gtk.StateFlags.NORMAL, Gdk.RGBA(1, 1, 1, 1))
            sp.set_size_request(-1, 55)
            sp.set_can_focus(False)
            sp.connect("clicked", wifi_kb_key, " ")
            ar.pack_start(sp, True, True, 0)
            bk = Gtk.Button(label="\u232b")
            bk.modify_font(Pango.FontDescription("Sans bold 14"))
            bk.override_background_color(Gtk.StateFlags.NORMAL, Gdk.RGBA(0.28, 0.28, 0.32, 1))
            bk.override_color(Gtk.StateFlags.NORMAL, Gdk.RGBA(1, 1, 1, 1))
            bk.set_size_request(80, 55)
            bk.set_can_focus(False)
            bk.connect("clicked", wifi_kb_bksp)
            ar.pack_start(bk, False, False, 0)
            kb.pack_start(ar, False, False, 0)
            self.main_box.pack_end(kb, False, False, 0)
            kb.show_all()
            self._wifi_kb_box = kb

        def hide_wifi_kb():
            if not self._wifi_kb_visible:
                return
            if self._wifi_kb_box:
                self._wifi_kb_box.destroy()
                self._wifi_kb_box = None
            self._wifi_overlay.set_valign(Gtk.Align.END)
            self._wifi_overlay.set_margin_top(0)
            self._wifi_overlay.set_margin_bottom(40)
            self._wifi_overlay.set_size_request(300, 350)
            self._wifi_kb_visible = False

        self._hide_wifi_kb_func = hide_wifi_kb

        # Auto-show keyboard when password field tapped
        self._wifi_pass_entry.connect("focus-in-event", lambda w, e: show_wifi_kb())

        # Save button
        save_btn = Gtk.Button(label="\u2714  Save & Connect")
        save_btn.get_style_context().add_class("wifi-connect-btn")
        save_btn.set_size_request(-1, 40)

        selected_net = {"ssid": None, "locked": False}

        def on_save(btn):
            ssid = selected_net["ssid"]
            if not ssid:
                p2_status.set_text("Please select a network first!")
                p2_status.override_color(Gtk.StateFlags.NORMAL, Gdk.RGBA(0.95, 0.2, 0.2, 1))
                return
            password = self._wifi_pass_entry.get_text()
            if selected_net["locked"] and not password:
                p2_status.set_text("Please enter the password!")
                p2_status.override_color(Gtk.StateFlags.NORMAL, Gdk.RGBA(0.95, 0.2, 0.2, 1))
                return
            # Immediate feedback
            save_btn.set_sensitive(False)
            save_btn.set_label("⏳  Connecting...")
            p2_status.set_text(f"Connecting to {ssid}...")
            p2_status.override_color(Gtk.StateFlags.NORMAL, Gdk.RGBA(0.59, 0.75, 0.98, 1))
            # Kill keyboard before connecting
            subprocess.run(["killall", "wvkbd-mobintl"], capture_output=True)
            if hasattr(self, '_hide_wifi_kb_func') and self._hide_wifi_kb_func:
                self._hide_wifi_kb_func()
            self._wifi_kb_visible = False
            def _restore_btn():
                save_btn.set_sensitive(True)
                save_btn.set_label("✔  Save & Connect")
            self._connect_to_wifi(ssid, password, p2_status, _restore_btn)

        save_btn.connect("clicked", on_save)
        self._wifi_pass_entry.connect("activate", on_save)
        page2.pack_start(save_btn, False, False, 4)
        page2.pack_start(p2_status, False, False, 2)

        stack.add_named(page2, "connect")

        # ========== Network select -> go to page 2 ==========
        def on_network_select(btn, ssid, locked):
            selected_net["ssid"] = ssid
            selected_net["locked"] = locked
            self._wifi_ssid_entry.set_text(ssid)
            self._wifi_pass_entry.set_text("")
            p2_status.set_text("")
            if locked:
                self._wifi_pass_entry.set_sensitive(True)
                self._wifi_pass_entry.set_placeholder_text("Enter password")
            else:
                self._wifi_pass_entry.set_sensitive(False)
                self._wifi_pass_entry.set_placeholder_text("No password needed")
            stack.set_visible_child_name("connect")

        def populate_networks(networks):
            for child in net_list.get_children():
                child.destroy()
            if not networks:
                no_net = Gtk.Label(label="No networks found")
                no_net.override_color(Gtk.StateFlags.NORMAL, Gdk.RGBA(0.6, 0.6, 0.6, 1))
                net_list.pack_start(no_net, False, False, 4)
            else:
                for net in networks:
                    row = Gtk.Button()
                    row.get_style_context().add_class("wifi-net-row")
                    row.set_relief(Gtk.ReliefStyle.NONE)
                    row.override_background_color(
                        Gtk.StateFlags.NORMAL, Gdk.RGBA(1, 1, 1, 0.06))

                    row_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
                    lock_icon = "\u26BF " if net["locked"] else ""
                    is_current = net.get("in_use", False)
                    name_text = f"{lock_icon}{net['ssid']}"
                    if is_current:
                        name_text += "  \u2714"

                    name_lbl = Gtk.Label(label=name_text)
                    name_lbl.get_style_context().add_class("wifi-net-name")
                    if is_current:
                        name_lbl.override_color(
                            Gtk.StateFlags.NORMAL, Gdk.RGBA(0.26, 0.85, 0.37, 1))
                    name_lbl.set_halign(Gtk.Align.START)
                    row_box.pack_start(name_lbl, True, True, 0)

                    sig_pct = net["signal"]
                    if sig_pct >= 75:
                        bars = "\u2582\u2584\u2586\u2588"
                    elif sig_pct >= 50:
                        bars = "\u2582\u2584\u2586"
                    elif sig_pct >= 25:
                        bars = "\u2582\u2584"
                    else:
                        bars = "\u2582"
                    sig_lbl = Gtk.Label(label=f"{bars} {sig_pct}%")
                    sig_lbl.get_style_context().add_class("wifi-net-signal")
                    row_box.pack_end(sig_lbl, False, False, 0)

                    row.add(row_box)
                    row.connect("clicked", on_network_select, net["ssid"], net["locked"])
                    net_list.pack_start(row, False, False, 0)
            net_list.show_all()

        def on_scan(btn):
            p1_status.set_text("Scanning...")
            p1_status.override_color(Gtk.StateFlags.NORMAL, Gdk.RGBA(0.59, 0.75, 0.98, 1))
            btn.set_sensitive(False)
            def do_scan():
                nets = self._scan_wifi_networks()
                def update_ui():
                    populate_networks(nets)
                    p1_status.set_text(f"Found {len(nets)} networks - tap to connect")
                    p1_status.override_color(Gtk.StateFlags.NORMAL, Gdk.RGBA(0.59, 0.75, 0.98, 1))
                    btn.set_sensitive(True)
                GLib.idle_add(update_ui)
            threading.Thread(target=do_scan, daemon=True).start()

        scan_btn.connect("clicked", on_scan)

        # Show list page first
        stack.set_visible_child_name("list")
        self._wifi_overlay.pack_start(stack, True, True, 0)

        # Auto-scan on open
        on_scan(scan_btn)

    def _close_wifi_popup(self):
        self._wifi_overlay.set_visible(False)
        # Close GTK keyboard if open
        if hasattr(self, '_hide_wifi_kb_func') and self._hide_wifi_kb_func:
            self._hide_wifi_kb_func()
        # Restore panda
        if hasattr(self, '_panda_event'):
            self._panda_event.set_visible(True)
        return False

    def _get_volume(self):
        """Get current volume percentage."""
        try:
            out = subprocess.run(
                ["amixer", "get", "Master"], capture_output=True, text=True, timeout=3
            )
            import re
            m = re.search(r"\[(\d+)%\]", out.stdout)
            if m:
                return int(m.group(1))
        except Exception:
            pass
        return 50

    def _set_volume(self, pct):
        """Set volume percentage."""
        pct = max(0, min(100, int(pct)))
        try:
            subprocess.run(
                ["amixer", "set", "Master", f"{pct}%"],
                capture_output=True, timeout=3
            )
        except Exception:
            pass

    def _on_speaker_clicked(self, button):
        """Show volume slider popup — dark rounded card centered on screen."""
        if self._volume_popup and self._volume_popup.get_visible():
            self._volume_popup.destroy()
            self._volume_popup = None
            return

        popup = Gtk.Window(type=Gtk.WindowType.POPUP)
        popup.set_transient_for(self)
        popup.set_decorated(False)
        popup.override_background_color(
            Gtk.StateFlags.NORMAL, Gdk.RGBA(0.06, 0.08, 0.14, 0.95))
        popup.set_size_request(420, 180)

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        box.set_margin_start(35)
        box.set_margin_end(35)
        box.set_margin_top(25)
        box.set_margin_bottom(25)

        # Speaker icon + "Volume" title centered
        title_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        title_box.set_halign(Gtk.Align.CENTER)
        speaker_da = Gtk.DrawingArea()
        speaker_da.set_size_request(30, 30)
        def draw_speaker(widget, cr):
            w = widget.get_allocated_width()
            h = widget.get_allocated_height()
            cr.set_source_rgba(1, 1, 1, 0.9)
            cr.rectangle(w * 0.15, h * 0.3, w * 0.2, h * 0.4)
            cr.fill()
            cr.move_to(w * 0.35, h * 0.3)
            cr.line_to(w * 0.55, h * 0.1)
            cr.line_to(w * 0.55, h * 0.9)
            cr.line_to(w * 0.35, h * 0.7)
            cr.close_path()
            cr.fill()
            cr.set_line_width(2)
            cr.set_line_cap(cairo.LINE_CAP_ROUND)
            for r in [6, 11]:
                cr.arc(w * 0.55, h * 0.5, r, -_math.pi * 0.35, _math.pi * 0.35)
                cr.stroke()
        speaker_da.connect("draw", draw_speaker)
        title_box.pack_start(speaker_da, False, False, 0)
        title = Gtk.Label(label="Volume")
        title.override_color(Gtk.StateFlags.NORMAL, Gdk.RGBA(1, 1, 1, 0.95))
        title.modify_font(Pango.FontDescription("Sans bold 24"))
        title_box.pack_start(title, False, False, 0)
        box.pack_start(title_box, False, False, 0)

        # Slider — wide blue
        current_vol = self._get_volume()
        scale = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 0, 100, 5)
        scale.set_value(current_vol)
        scale.set_size_request(350, 40)
        scale.set_draw_value(False)
        box.pack_start(scale, False, False, 0)

        # Percentage label centered
        vol_label = Gtk.Label(label=f"{current_vol}%")
        vol_label.override_color(Gtk.StateFlags.NORMAL, Gdk.RGBA(0.6, 0.75, 0.95, 0.85))
        vol_label.modify_font(Pango.FontDescription("Sans 22"))
        vol_label.set_halign(Gtk.Align.CENTER)
        box.pack_start(vol_label, False, False, 0)

        def on_volume_changed(s):
            val = int(s.get_value())
            vol_label.set_text(f"{val}%")
            self._set_volume(val)

        scale.connect("value-changed", on_volume_changed)
        popup.add(box)

        popup.move(5, 500)
        popup.show_all()
        self._volume_popup = popup

        # Auto-close after 6 seconds
        GLib.timeout_add(6000, self._close_volume_popup)

    def _close_volume_popup(self):
        if self._volume_popup:
            self._volume_popup.destroy()
            self._volume_popup = None
        return False

    def _on_logout(self, button):
        global _announce_stop, _auto_announcing
        # If announce is running, stop it first then logout
        if _auto_announcing:
            # Let announce complete, then logout
            def wait_and_logout():
                while _auto_announcing:
                    time.sleep(0.5)
                GLib.idle_add(self._do_logout)
            button.set_sensitive(False)
            threading.Thread(target=wait_and_logout, daemon=True).start()
            return
        self._do_logout()

    def _do_logout(self):
        global USERNAME, PASSWORD, LOGGED_IN
        USERNAME = ""
        PASSWORD = ""
        LOGGED_IN = False
        subprocess.run(["rm", "-f", CREDS_FILE], capture_output=True)
        subprocess.run(["killall", "aplay"], capture_output=True)
        self.refresh_label.set_text("Logging out...")
        def _create_login():
            self.hide()
            login = LoginWindow()
            login.connect("destroy", lambda w: None if LOGGED_IN else Gtk.main_quit())
            login.show_all()
            self.destroy()
            return False
        GLib.timeout_add(200, _create_login)
        self.destroy()

    def _on_lang_changed(self, combo):
        global TTS_LANG
        idx = combo.get_active()
        TTS_LANG = self._lang_list[idx]
        # Save to admin config
        try:
            import json
            if os.path.exists(ADMIN_CONFIG):
                with open(ADMIN_CONFIG) as f:
                    cfg = json.load(f)
                cfg["tts_lang"] = TTS_LANG
                with open(ADMIN_CONFIG, "w") as f:
                    json.dump(cfg, f)
        except: pass
        # Clear audio cache for new language
        _audio_cache.clear()

    def on_refresh_clicked(self, button):
        global _announce_stop
        _announce_stop = False
        self._loading_active = True
        self._loading_phase = 0
        self._show_loading()
        self._countdown = REFRESH_INTERVAL
        button.set_sensitive(False)
        def do_refresh():
            self._fetch_and_update()
            GLib.idle_add(button.set_sensitive, True)
        threading.Thread(target=do_refresh, daemon=True).start()

    def _quick_retry(self):
        """Quick retry after fetch failure."""
        print(f"[{now()}] Quick retry fetch...")
        threading.Thread(target=self._fetch_and_update, daemon=True).start()
        return False  # Don't repeat

    def first_fetch(self):
        def _first_fetch_with_retry():
            for attempt in range(5):
                data = fetch_alerts()
                if data:
                    GLib.idle_add(self._render_alerts, data)
                    today = data.get("generalAlerts", {}).get("alerts", {}).get("today", [])
                    if today:
                        threading.Thread(target=precache_audio, args=(today,), daemon=True).start()
                    return
                print(f"[{now()}] First fetch attempt {attempt+1}/5 failed, retrying in {3*(attempt+1)}s...")
                time.sleep(3 * (attempt + 1))
            GLib.idle_add(self._render_alerts, None)
        threading.Thread(target=_first_fetch_with_retry, daemon=True).start()
        return False

    def refresh_alerts(self):
        threading.Thread(target=self._fetch_and_update, daemon=True).start()
        return True

    _last_fetch_time_actual = 0

    def _fetch_and_update(self):
        global _refresh_queued, token, token_time
        # If announce is running, queue the refresh
        if _auto_announcing:
            _refresh_queued = True
            print("[" + now() + "] Refresh queued - announce in progress")
            return
        # Prevent fetching more than once every 15 seconds
        now_ts = time.time()
        if now_ts - self._last_fetch_time_actual < 15:
            return
        self._last_fetch_time_actual = now_ts

        data = fetch_alerts()

        # If failed, refresh token and retry
        if not data:
            print(f"[{now()}] Fetch failed, refreshing token and retrying...")
            token = ""
            token_time = 0
            time.sleep(2)
            data = fetch_alerts()

        # If still failed, wait and try once more
        if not data:
            print(f"[{now()}] Second attempt failed, retrying in 5s...")
            time.sleep(5)
            token = ""
            token_time = 0
            data = fetch_alerts()

        # Pre-cache audio for instant playback
        if data:
            today = data.get("generalAlerts", {}).get("alerts", {}).get("today", [])
            if today:
                threading.Thread(target=precache_audio, args=(today,), daemon=True).start()
        GLib.idle_add(self._render_alerts, data)

    def _render_alerts(self, data):
        # Stop loading animation
        self._loading_active = False
        # Clear old alerts
        for child in self.alerts_container.get_children():
            self.alerts_container.remove(child)

        if not data:
            # Track consecutive failures for escalating retry
            if not hasattr(self, '_fail_count'):
                self._fail_count = 0
            self._fail_count += 1
            retry_delay = min(10 * self._fail_count, 60)  # 10s, 20s, 30s... max 60s

            lbl = Gtk.Label(label=f"Network error. Retrying in {retry_delay}s...")
            lbl.get_style_context().add_class("no-alerts")
            lbl.override_color(Gtk.StateFlags.NORMAL, Gdk.RGBA(1, 0.4, 0.4, 1))
            self.alerts_container.pack_start(lbl, True, True, 20)
            prev = f" | Last success: {self._last_refresh_time}" if self._last_refresh_time else ""
            self.refresh_label.set_text(f"Network error (attempt {self._fail_count}) | Retry in {retry_delay}s{prev}")
            self._last_fetch_time_actual = 0  # Reset throttle for retry
            GLib.timeout_add_seconds(retry_delay, self._quick_retry)
            self.alerts_container.show_all()
            return

        # Reset fail counter on success
        self._fail_count = 0

        general = data.get("generalAlerts", {})
        offline = data.get("offlineAlerts", {})
        meta = general.get("meta", {})

        # Update stats
        self.stat_unread[1].set_text(str(meta.get("unread", 0)))
        self.stat_read[1].set_text(str(meta.get("read", 0)))
        self.stat_total[1].set_text(str(meta.get("total", 0)))
        off_count = len(offline.get("alerts", {}).get("today", []))
        self.stat_offline[1].set_text(str(off_count))

        # General alerts - split into Unread and Read sections
        today_alerts = general.get("alerts", {}).get("today", [])
        unread_alerts = [a for a in today_alerts if not a.get("isRead", True)]
        read_alerts = [a for a in today_alerts if a.get("isRead", True)]

        # Store alerts for "Announce All"
        self._all_today_alerts = today_alerts

        if not today_alerts:
            lbl = Gtk.Label(label="No alerts today")
            lbl.get_style_context().add_class("no-alerts")
            self.alerts_container.pack_start(lbl, True, True, 20)
        else:
            # ---- ANNOUNCE ALL BUTTON ----
            btn_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
            btn_row.set_margin_start(10)
            btn_row.set_margin_end(10)
            btn_row.set_margin_top(4)
            btn_row.set_margin_bottom(4)

            announce_all_btn = Gtk.Button(label="\u266A  Announce All Alerts")
            announce_all_btn.get_style_context().add_class("btn-announce")
            announce_all_btn.connect("clicked", self._on_announce_all)
            btn_row.pack_start(announce_all_btn, True, True, 0)

            self.alerts_container.pack_start(btn_row, False, False, 0)

            # ---- UNREAD SECTION ----
            self._section_unread = Gtk.Label(label="")
            self._section_unread.set_size_request(-1, 0)
            self.alerts_container.pack_start(self._section_unread, False, False, 0)
            unread_header = Gtk.Label(label=f"\u25CF  UNREAD ({len(unread_alerts)})")
            unread_header.get_style_context().add_class("section-header")
            unread_header.set_halign(Gtk.Align.START)
            unread_header.override_color(Gtk.StateFlags.NORMAL, Gdk.RGBA(0.97, 0.33, 0.33, 1))
            self.alerts_container.pack_start(unread_header, False, False, 0)

            if unread_alerts:
                for alert in unread_alerts:
                    card = self._make_alert_card(alert)
                    self.alerts_container.pack_start(card, False, False, 0)
                # Auto-announce only NEW unread alerts (not already announced)
                new_unread = [a for a in unread_alerts if a.get('id','') not in announced_ids]
                if new_unread and not _auto_announcing:
                    threading.Thread(target=self._auto_announce_unread, args=(list(new_unread),), daemon=True).start()
            else:
                no_unread = Gtk.Label(label="All caught up! No unread alerts.")
                no_unread.override_color(Gtk.StateFlags.NORMAL, Gdk.RGBA(0.26, 0.77, 0.37, 0.8))
                no_unread.modify_font(Pango.FontDescription("Sans 14"))
                no_unread.set_margin_top(6)
                no_unread.set_margin_bottom(6)
                self.alerts_container.pack_start(no_unread, False, False, 0)

            # ---- SEPARATOR ----
            sep = Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL)
            sep.override_background_color(Gtk.StateFlags.NORMAL, Gdk.RGBA(0.2, 0.25, 0.33, 1))
            self.alerts_container.pack_start(sep, False, False, 6)

            # ---- READ SECTION ----
            self._section_read = Gtk.Label(label="")
            self._section_read.set_size_request(-1, 0)
            self.alerts_container.pack_start(self._section_read, False, False, 0)
            read_header = Gtk.Label(label=f"\u25CF  READ ({len(read_alerts)})")
            read_header.get_style_context().add_class("section-header")
            read_header.set_halign(Gtk.Align.START)
            read_header.override_color(Gtk.StateFlags.NORMAL, Gdk.RGBA(0.26, 0.77, 0.37, 1))
            self.alerts_container.pack_start(read_header, False, False, 0)

            if read_alerts:
                for alert in read_alerts:
                    card = self._make_alert_card(alert)
                    self.alerts_container.pack_start(card, False, False, 0)
            else:
                no_read = Gtk.Label(label="No read alerts yet.")
                no_read.override_color(Gtk.StateFlags.NORMAL, Gdk.RGBA(0.58, 0.64, 0.72, 0.7))
                no_read.modify_font(Pango.FontDescription("Sans 14"))
                no_read.set_margin_top(6)
                no_read.set_margin_bottom(6)
                self.alerts_container.pack_start(no_read, False, False, 0)

        # Offline alerts
        offline_list = offline.get("alerts", {}).get("today", [])
        self._all_offline_alerts = offline_list
        self._section_offline = Gtk.Label(label="")
        self._section_offline.set_size_request(-1, 0)
        self.alerts_container.pack_start(self._section_offline, False, False, 0)
        if offline_list:
            # Announce Offline button
            off_btn_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
            off_btn_row.set_margin_start(10)
            off_btn_row.set_margin_end(10)
            off_btn_row.set_margin_top(4)
            off_btn_row.set_margin_bottom(4)

            announce_off_btn = Gtk.Button(label="♪  Announce Offline Units")
            announce_off_btn.get_style_context().add_class("btn-announce")
            announce_off_btn.modify_font(Pango.FontDescription("Sans bold 18"))
            announce_off_btn.connect("clicked", self._on_announce_offline)
            off_btn_row.pack_start(announce_off_btn, True, True, 0)
            self.alerts_container.pack_start(off_btn_row, False, False, 0)

            sec_label = Gtk.Label(label=f"OFFLINE UNITS ({len(offline_list)})")
            sec_label.get_style_context().add_class("section-header")
            sec_label.set_halign(Gtk.Align.START)
            self.alerts_container.pack_start(sec_label, False, False, 4)

            for alert in offline_list:
                card = self._make_offline_card(alert)
                self.alerts_container.pack_start(card, False, False, 0)

        self._last_refresh_time = datetime.now().strftime('%I:%M:%S %p')
        self._countdown = REFRESH_INTERVAL
        self.alerts_container.show_all()

    def _make_alert_card(self, alert):
        importance = alert.get("importanceLevel", "info")
        colors = COLORS.get(importance, COLORS["info"])
        is_unread = not alert.get("isRead", True)

        is_announced_alert = False  # Always allow re-announce

        card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        card.get_style_context().add_class("alert-card")

        bg_rgba = self._hex_to_rgba(colors["bg"])
        card.override_background_color(Gtk.StateFlags.NORMAL, Gdk.RGBA(*bg_rgba))

        # Top row: status dot + title + badge + time
        top = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)

        # Unread/Read indicator
        if is_unread:
            dot = Gtk.Label(label="\u25CF")  # Filled circle
            dot.get_style_context().add_class("unread-dot")
            dot.override_color(Gtk.StateFlags.NORMAL, Gdk.RGBA(0.94, 0.27, 0.27, 1))
            dot.set_tooltip_text("Unread - will be marked read after announcement")
        else:
            dot = Gtk.Label(label="\u25CF")  # Green filled circle
            dot.get_style_context().add_class("read-check")
            dot.override_color(Gtk.StateFlags.NORMAL, Gdk.RGBA(0.13, 0.77, 0.37, 1))
            dot.set_tooltip_text("Read" + (" & Announced" if is_announced_alert else ""))
        top.pack_start(dot, False, False, 0)

        title = Gtk.Label(label=alert.get("title", "Unknown"))
        title.get_style_context().add_class("alert-title")
        if is_unread:
            title.get_style_context().add_class("alert-unread")
        title.override_color(Gtk.StateFlags.NORMAL, Gdk.RGBA(*self._hex_to_rgba(colors["text"])))
        title.set_halign(Gtk.Align.START)
        title.set_ellipsize(Pango.EllipsizeMode.END)
        title.set_max_width_chars(28)
        top.pack_start(title, True, True, 0)

        # Badge
        badge = Gtk.Label(label=importance.upper())
        badge.get_style_context().add_class("alert-badge")
        badge.override_background_color(
            Gtk.StateFlags.NORMAL,
            Gdk.RGBA(*self._hex_to_rgba(colors["badge"]))
        )
        top.pack_end(badge, False, False, 0)

        # Time
        time_str = alert.get("time", "")
        time_label = Gtk.Label(label=time_str)
        time_label.get_style_context().add_class("alert-time")
        top.pack_end(time_label, False, False, 4)

        card.pack_start(top, False, False, 0)

        # Body
        body_text = alert.get("body", "")
        if body_text:
            body = Gtk.Label(label=body_text)
            body.get_style_context().add_class("alert-body")
            body.override_color(Gtk.StateFlags.NORMAL, Gdk.RGBA(*self._hex_to_rgba(colors["text"])))
            body.set_halign(Gtk.Align.START)
            body.set_line_wrap(True)
            card.pack_start(body, False, False, 0)

        # Details
        desc = alert.get("description", {})
        details = desc.get("details", [])
        if details:
            detail_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=1)
            detail_box.get_style_context().add_class("alert-detail")
            for d in details[:3]:
                dl = Gtk.Label(label=f"  {d}")
                dl.get_style_context().add_class("alert-detail")
                dl.set_halign(Gtk.Align.START)
                dl.set_line_wrap(True)
                dl.override_color(Gtk.StateFlags.NORMAL, Gdk.RGBA(*self._hex_to_rgba(colors["text"])))
                detail_box.pack_start(dl, False, False, 0)
            card.pack_start(detail_box, False, False, 0)

        # Action buttons - always visible
        actions = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        actions.get_style_context().add_class("alert-actions")

        if is_unread:
            read_btn = Gtk.Button(label="\u25CF  Mark Read")
            read_btn.get_style_context().add_class("btn-mark-read")
            read_btn.connect("clicked", self._on_mark_read, alert)
            actions.pack_start(read_btn, False, False, 0)

        announce_btn = Gtk.Button(label="\u266A  Announce")
        announce_btn.get_style_context().add_class("btn-announce")
        announce_btn.connect("clicked", self._on_announce, alert)
        actions.pack_start(announce_btn, False, False, 0)

        card.pack_start(actions, False, False, 0)

        return card

    def _auto_announce_unread(self, alerts):
        """Auto-announce unread alerts one by one."""
        global _auto_announcing, announced_ids
        if _auto_announcing:
            return
        _auto_announcing = True
        try:
            _start_announcing()
            time.sleep(3)

            for i, alert in enumerate(alerts):
                if _announce_stop:
                    break
                title = alert.get("title", "")
                body = alert.get("body", "")
                desc = alert.get("description", {})
                status = desc.get("status", "")
                t = TRANSLATIONS.get(TTS_LANG, TRANSLATIONS["en"])
                _, t_body, t_status = translate_alert_text(title, body, status, TTS_LANG)
                text = t["unread_alert"] + " " + str(i+1) + " " + t["of"] + " " + str(len(alerts)) + ". " + title + ". " + t_body + ". " + t_status

                try:
                    aid = alert.get("id", "")
                    wav_path = _audio_cache.get(aid)
                    if not wav_path or not os.path.exists(str(wav_path)):
                        mp3_path = "/tmp/auto_unread_" + str(i) + ".mp3"
                        wav_path = "/tmp/auto_unread_" + str(i) + ".wav"
                        if _announce_stop: break
                        if not _tts_generate(text, TTS_LANG, mp3_path, wav_path):
                            continue

                    audio_dur = 0
                    try:
                        audio_dur = os.path.getsize(wav_path) / (44100 * 2)
                    except:
                        audio_dur = 5
                    GLib.idle_add(self._start_typing, text, audio_dur)
                    subprocess.run(["aplay", "-D", "plughw:0,0", "-q", wav_path], capture_output=True, timeout=30)
                    # Wait for typing to finish
                    for _ in range(200):
                        if self._typing_done or _announce_stop:
                            break
                        time.sleep(0.02)
                    time.sleep(0.5)
                except Exception as e:
                    print("[" + now() + "] Auto-announce unread error: " + str(e))

                announced_ids.add(alert.get("id", ""))
                announce_and_mark_read(alert)
                GLib.idle_add(self._update_counters, 1)
                time.sleep(0.5)

            print("[" + now() + "] Auto-announced " + str(len(alerts)) + " unread alerts")
        finally:
            _auto_announcing = False
            _stop_announcing()
            global _refresh_queued
            if _refresh_queued:
                _refresh_queued = False
                GLib.idle_add(self.refresh_alerts)

    def _auto_announce_offline_timer(self):
        """Auto-announce offline alerts every 1 hour."""
        if not self._all_offline_alerts:
            return True
        print("[" + now() + "] Auto-announcing " + str(len(self._all_offline_alerts)) + " offline alerts (hourly)")

        def do_offline_auto():
            import subprocess
            _start_announcing()
            alerts = list(self._all_offline_alerts)

            for i, alert in enumerate(alerts):
                if _announce_stop:
                    break
                title = alert.get("title", "")
                desc = alert.get("description", {})
                status = desc.get("status", "")
                t = TRANSLATIONS.get(TTS_LANG, TRANSLATIONS["en"])
                _, _, t_status = translate_alert_text(title, "", status, TTS_LANG)
                text = t["offline_unit"] + " " + str(i+1) + " " + t["of"] + " " + str(len(alerts)) + ". " + title + ". " + t_status

                try:
                    mp3_path = "/tmp/auto_offline_" + str(i) + ".mp3"
                    wav_path = "/tmp/auto_offline_" + str(i) + ".wav"
                    if _announce_stop: break
                    if not _tts_generate(text, TTS_LANG, mp3_path, wav_path):
                        continue
                    GLib.idle_add(self._start_typing, text)
                    subprocess.run(["aplay", "-D", "plughw:0,0", "-q", wav_path], capture_output=True, timeout=30)
                    time.sleep(1)
                except Exception as e:
                    print("[" + now() + "] Auto offline announce error: " + str(e))
                time.sleep(0.5)

        threading.Thread(target=do_offline_auto, daemon=True).start()
        return True  # Keep timer  # Keep timer running

    def _on_announce_offline(self, button):
        """Announce all offline units."""
        if _auto_announcing:
            return
        alerts = self._all_offline_alerts
        if not alerts:
            return
        button.set_sensitive(False)
        button.set_label(f"Announcing {len(alerts)} offline units...")

        def do_offline():
            import subprocess
            _start_announcing()
            self._batch_announcing = True
            total = len(alerts)

            # Pre-generate all audio
            GLib.idle_add(button.set_label, "Generating audio...")
            audio_files = []
            texts = []
            for i, alert in enumerate(alerts):
                if _announce_stop:
                    break
                title = alert.get("title", "")
                desc = alert.get("description", {})
                status = desc.get("status", "")
                t = TRANSLATIONS.get(TTS_LANG, TRANSLATIONS["en"])
                _, _, t_status = translate_alert_text(title, "", status, TTS_LANG)
                text = t["offline_unit"] + " " + str(i+1) + " " + t["of"] + " " + str(total) + ". " + title + ". " + t_status
                texts.append(text)
                try:
                    mp3_path = "/tmp/offline_" + str(i) + ".mp3"
                    wav_path = "/tmp/offline_" + str(i) + ".wav"
                    if _announce_stop: break
                    if _tts_generate(text, TTS_LANG, mp3_path, wav_path):
                        audio_files.append(wav_path)
                    else:
                        audio_files.append(None)
                except Exception as e:
                    audio_files.append(None)

            # Play each with animation
            GLib.idle_add(button.set_label, "Playing offline alerts...")
            for i, alert in enumerate(alerts):
                if _announce_stop:
                    break
                if i >= len(audio_files) or not audio_files[i]:
                    continue

                audio_duration = 0
                try:
                    audio_duration = os.path.getsize(audio_files[i]) / (44100 * 2)
                except:
                    audio_duration = 5

                self._typing_done = False
                GLib.idle_add(self._start_typing, texts[i], audio_duration)
                time.sleep(0.3)

                audio_proc = subprocess.Popen(["aplay", "-D", "plughw:0,0", "-q", audio_files[i]], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                while audio_proc.poll() is None:
                    if _announce_stop:
                        audio_proc.kill()
                        break
                    time.sleep(0.1)

                for _ in range(100):
                    if self._typing_done or _announce_stop:
                        break
                    time.sleep(0.01)

                time.sleep(0.5)

            self._batch_announcing = False
            _stop_announcing()
            if _refresh_queued:
                _refresh_queued = False
                time.sleep(1)
                GLib.idle_add(self.refresh_alerts)
            GLib.idle_add(self._after_announce_offline, button)

        threading.Thread(target=do_offline, daemon=True).start()

    def _after_announce_offline(self, button):
        button.set_label("♪  Announce Offline Units")
        button.set_sensitive(True)

    def _on_announce_all(self, button):
        """Announce all alerts one by one."""
        if _auto_announcing:
            return
        alerts = self._all_today_alerts
        if not alerts:
            return
        button.set_sensitive(False)
        button.set_label(f"Announcing {len(alerts)} alerts...")

        def do_all():
            global _auto_announcing
            _auto_announcing = True
            _start_announcing()
            for i, alert in enumerate(alerts):
                if _announce_stop:
                    print(f"[{now()}] Announce all cancelled at alert {i+1}")
                    break
                title = alert.get("title", "")
                body = alert.get("body", "")
                desc = alert.get("description", {})
                status = desc.get("status", "")
                t = TRANSLATIONS.get(TTS_LANG, TRANSLATIONS["en"])
                _, t_body, t_status = translate_alert_text(title, body, status, TTS_LANG)
                text = t["alert"] + ". " + title + ". " + t_body + ". " + t_status

                # Generate audio first
                try:
                    aid = alert.get("id", "")
                    wav_path = _audio_cache.get(aid)
                    if not wav_path or not os.path.exists(wav_path):
                        mp3_path = "/tmp/aquabox_announce_all.mp3"
                        wav_path = "/tmp/aquabox_announce_all.wav"
                        if _announce_stop: break
                        if not _tts_generate(text, TTS_LANG, mp3_path, wav_path):
                            continue
                    GLib.idle_add(self._start_typing, text)
                    subprocess.run(["aplay", "-D", "plughw:0,0", "-q", wav_path], capture_output=True, timeout=30)
                    # Wait for typing animation to catch up with audio
                    time.sleep(1)
                except Exception as e:
                    print(f"[{now()}] Announce all TTS error: {e}")

                announce_and_mark_read(alert)
                time.sleep(0.5)

            self._batch_announcing = False
            _auto_announcing = False
            _stop_announcing()
            # Process queued refresh
            if _refresh_queued:
                _refresh_queued = False
                time.sleep(1)
                GLib.idle_add(self.refresh_alerts)
            GLib.idle_add(self._after_announce_all, button)

        threading.Thread(target=do_all, daemon=True).start()

    def _after_announce_all(self, button):
        """Update UI after announcing all - re-enable button."""
        global _auto_announcing
        _auto_announcing = False
        button.set_sensitive(True)
        button.set_label("\u266A  Announce All Alerts")
        button.get_style_context().remove_class("btn-done")
        button.get_style_context().add_class("btn-announce")
        threading.Thread(target=self._fetch_and_update, daemon=True).start()

    def _on_mark_read(self, button, alert):
        """Mark single alert as read."""
        button.set_sensitive(False)
        button.set_label("Marking...")
        def do_mark():
            mark_alerts_as_read([alert])
            GLib.idle_add(self._after_mark_read, button)
        threading.Thread(target=do_mark, daemon=True).start()

    def _after_mark_read(self, button):
        """Update UI after marking read."""
        button.set_label("\u25CF  Done")
        button.get_style_context().remove_class("btn-mark-read")
        button.get_style_context().add_class("btn-done")
        # Refresh to move alert to Read section
        threading.Thread(target=self._fetch_and_update, daemon=True).start()

    def _on_announce(self, button, alert):
        """Announce alert via TTS with typing animation."""
        if _auto_announcing:
            return
        button.set_sensitive(False)
        button.set_label("Speaking...")

        title = alert.get("title", "")
        body = alert.get("body", "")
        desc = alert.get("description", {})
        status = desc.get("status", "")
        _, t_body_s, t_status_s = translate_alert_text(title, body, status, TTS_LANG)
        text = title + ". " + t_body_s + ". " + t_status_s

        def do_announce():
            global _auto_announcing
            _auto_announcing = True
            _start_announcing()
            try:
                import subprocess
                aid = alert.get("id", "")
                wav_path = _audio_cache.get(aid)
                if not wav_path or not os.path.exists(wav_path):
                    mp3_path = "/tmp/aquabox_announce.mp3"
                    wav_path = "/tmp/aquabox_announce.wav"
                    if _announce_stop: pass
                    if not _tts_generate(text, TTS_LANG, mp3_path, wav_path):
                        raise Exception("TTS generation failed")
                audio_dur = 0
                try:
                    audio_dur = os.path.getsize(wav_path) / (44100 * 2)
                except:
                    audio_dur = 5
                GLib.idle_add(self._start_typing, text, audio_dur)
                subprocess.run(["aplay", "-D", "plughw:0,0", "-q", wav_path], capture_output=True, timeout=30)
            except Exception as e:
                print(f"[{now()}] Announce TTS error: {e}")

            if not _announce_stop:
                announce_and_mark_read(alert)
            _stop_announcing()
            GLib.idle_add(self._after_announce, button)
        threading.Thread(target=do_announce, daemon=True).start()

    def _start_typing(self, text, duration=0):
        """Start typing animation. duration=estimated audio seconds."""
        self._typing_done = False
        # Cancel any pending hide timer from previous alert
        if self._hide_timer:
            try:
                GLib.source_remove(self._hide_timer)
            except Exception:
                pass
            self._hide_timer = None
        # Cancel any running typing timer
        if self._typing_timer:
            try:
                GLib.source_remove(self._typing_timer)
            except Exception:
                pass
            self._typing_timer = None
        self._typing_text = "\u266A ANNOUNCING: " + text
        self._typing_index = 0
        # Calculate speed: text must finish in 'duration' seconds
        # If no duration given, use 60 WPM default
        total_chars = len(self._typing_text)
        if duration > 0 and total_chars > 0:
            self._typing_speed = max(10, int((duration * 1000 * 0.85) / total_chars))
        else:
            self._typing_speed = 55  # default
        self.overlay_label.set_text("")
        self.overlay_container.set_no_show_all(False)
        self.overlay_container.show_all()
        self.overlay_container.set_visible(True)
        self.announce_label.set_text("")
        self.announce_bar.show()
        self.announce_label.show()
        self.announce_bar.set_visible(True)

        print(f"[{now()}] Typing started: {text[:50]}...")
        self._typing_timer = GLib.timeout_add(self._typing_speed, self._typing_tick)

    def _typing_tick(self):
        """Type one character per tick."""
        if self._typing_index <= len(self._typing_text):
            shown = self._typing_text[:self._typing_index] + "\u2588"
            self.overlay_label.set_text(shown)
            self.announce_label.set_text(shown)
            self._typing_index += 1
            return True
        else:
            done = self._typing_text + "  \u2713"
            self.overlay_label.set_text(done)
            self.announce_label.set_text(done)
            self._typing_timer = None
            print(f"[{now()}] Typing complete")
            if not self._batch_announcing:
                self._hide_timer = GLib.timeout_add(5000, self._hide_announce_overlay)
            return False

    def _cancel_announce(self):
        """Cancel ongoing announcement."""
        global _announce_stop, _auto_announcing
        _announce_stop = True
        _auto_announcing = False
        self._typing_done = True
        self._batch_announcing = False
        import subprocess
        subprocess.run(["killall", "aplay"], capture_output=True)
        self._hide_announce_overlay()
        # Reset all announce buttons immediately without waiting for API
        GLib.idle_add(self._reset_announce_buttons)
        print(f"[{now()}] Announcement cancelled")

    def _reset_announce_buttons(self):
        """Reset all announce buttons to clickable state immediately."""
        # Re-enable all individual announce buttons in the alerts container
        def _reset_children(container):
            for child in container.get_children():
                if isinstance(child, Gtk.Button):
                    label = child.get_label() or ""
                    if "Speaking" in label or "Announced" in label or "Announcing" in label:
                        child.set_sensitive(True)
                        child.set_label("\u266A  Announce")
                        child.get_style_context().remove_class("btn-done")
                        child.get_style_context().add_class("btn-announce")
                    elif "All Announced" in label:
                        child.set_sensitive(True)
                        child.set_label("\u266A  Announce All Alerts")
                        child.get_style_context().remove_class("btn-done")
                        child.get_style_context().add_class("btn-announce")
                elif isinstance(child, Gtk.Box):
                    _reset_children(child)
        _reset_children(self.alerts_container)

    def _hide_announce_overlay(self):
        """Hide overlay and bottom bar."""
        self.overlay_container.set_visible(False)
        self.overlay_container.set_no_show_all(True)
        self.overlay_container.hide()
        self.announce_bar.hide()
        self.announce_bar.set_visible(False)
        self._typing_timer = None
        return False

    def _after_announce(self, button):
        """Update UI after announcement - re-enable button for reuse."""
        global _auto_announcing
        _auto_announcing = False
        button.set_sensitive(True)
        button.set_label("\u266A  Announce")
        button.get_style_context().remove_class("btn-done")
        button.get_style_context().add_class("btn-announce")

    def _make_offline_card(self, alert):
        card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        card.get_style_context().add_class("offline-card")

        top = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        title = Gtk.Label(label=alert.get("title", "Unknown"))
        title.get_style_context().add_class("offline-title")
        title.set_halign(Gtk.Align.START)
        title.set_ellipsize(Pango.EllipsizeMode.END)
        top.pack_start(title, True, True, 0)

        time_label = Gtk.Label(label=alert.get("time", ""))
        time_label.get_style_context().add_class("alert-time")
        top.pack_end(time_label, False, False, 0)
        card.pack_start(top, False, False, 0)

        body = Gtk.Label(label=alert.get("body", ""))
        body.get_style_context().add_class("offline-body")
        body.set_halign(Gtk.Align.START)
        body.set_line_wrap(True)
        card.pack_start(body, False, False, 0)

        return card

    def _hex_to_rgba(self, hex_color):
        h = hex_color.lstrip("#")
        r, g, b = int(h[0:2], 16)/255, int(h[2:4], 16)/255, int(h[4:6], 16)/255
        return (r, g, b, 1.0)


# ==================== MAIN ====================
def main():
    signal.signal(signal.SIGINT, lambda s, f: Gtk.main_quit())
    signal.signal(signal.SIGTERM, lambda s, f: Gtk.main_quit())

    os.environ["WAYLAND_DISPLAY"] = "wayland-0"
    os.environ["XDG_RUNTIME_DIR"] = "/run/user/1000"
    os.environ["GDK_BACKEND"] = "wayland"

    load_announced()

    print("=" * 50)
    print("  AquaBox Alerts Display")
    print(f"  Refresh: every {REFRESH_INTERVAL}s")
    print(f"  Announced alerts tracked: {len(announced_ids)}")
    print("=" * 50)

    load_admin_config()
    load_session()

    if LOGGED_IN:
        # Saved session - go directly to alerts
        win = AlertsWindow()
        win.connect("destroy", lambda w: Gtk.main_quit() if LOGGED_IN else None)
        win.show_all()
    else:
        # Show login screen
        login = LoginWindow()
        login.connect("destroy", lambda w: None if LOGGED_IN else Gtk.main_quit())
        login.show_all()

    Gtk.main()


if __name__ == "__main__":
    main()
