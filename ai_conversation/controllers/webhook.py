import logging
from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)

class AIWebhookController(http.Controller):

    @http.route('/api/ai/webhook', type='json', auth='public', methods=['POST'], csrf=False)
    def receive_ai_results(self, **post):
        # We use auth='public' but should validate an API Key from headers in production
        data = request.get_json_data()
        job_id = data.get('job_id')
        status = data.get('status')
        
        if not job_id:
            return {'error': 'Missing job_id'}
            
        conversation = request.env['ai.conversation'].sudo().search([('job_id', '=', job_id)], limit=1)
        if not conversation:
            return {'error': 'Conversation not found'}
            
        if status == 'failed':
            conversation.write({
                'state': 'failed',
                'summary': f"<p>Error: {data.get('error', 'Unknown Error')}</p>"
            })
            return {'status': 'success'}
            
        # Parse successful result
        result = data.get('result', {})
        conversation.write({
            'state': 'done',
            'raw_transcript': data.get('raw_transcript'),
            'summary': result.get('summary', '')
        })
        
        # Create Speaker entries
        speakers_data = result.get('speakers', [])
        for spk in speakers_data:
            request.env['ai.conversation.speaker'].sudo().create({
                'conversation_id': conversation.id,
                'speaker_name': spk.get('name'),
                'text': spk.get('dialogue'),
                'timestamp_start': spk.get('time')
            })
            
        # Create Action items
        actions_data = result.get('action_items', [])
        for act in actions_data:
            request.env['ai.conversation.action'].sudo().create({
                'conversation_id': conversation.id,
                'description': act.get('task'),
                'assignee_name': act.get('assignee'),
                'deadline': act.get('deadline')
            })
            
        return {'status': 'success'}
