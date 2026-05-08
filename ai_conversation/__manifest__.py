{
    'name': 'AI Conversation Intelligence',
    'version': '19.0.1.0.0',
    'category': 'Productivity/AI',
    'summary': 'AI Transcription & Conversation Intelligence Platform',
    'description': """
        Integrates with FastAPI AI Service for audio processing, 
        transcription (Whisper/Gemini), and LLM insights extraction.
    """,
    'author': 'Deni Labs',
    'website': 'https://github.com/deninasrullah',
    'depends': ['base', 'mail', 'crm', 'project'],
    'data': [
        'security/ir.model.access.csv',
        'views/ai_conversation_views.xml',
    ],
    'installable': True,
    'application': True,
    'license': 'LGPL-3',
}
